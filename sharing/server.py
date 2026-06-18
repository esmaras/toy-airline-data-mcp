"""
Delta Sharing REST server — FastAPI implementation.

Supports two storage modes:
  - Local (default): serves parquet files as static HTTP from delta_tables/
  - S3 (set DELTA_TABLES_S3_PREFIX env var): returns presigned S3 URLs

Run locally:
    uvicorn sharing.server:app --host 0.0.0.0 --port 8080 --reload
"""

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import pyarrow as pa
from deltalake import DeltaTable
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from sharing.config_loader import (
    get_shares,
    get_schemas,
    get_tables,
    get_table_path,
    load_config,
)

PROJECT_ROOT = Path(__file__).parent.parent
DELTA_TABLES_DIR = PROJECT_ROOT / "delta_tables"
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
_S3_MODE = bool(os.getenv("DELTA_TABLES_S3_PREFIX", ""))
_PRESIGNED_URL_TTL = 3600  # seconds

app = FastAPI(title="Southwest Airline Delta Sharing Server")

if not _S3_MODE and DELTA_TABLES_DIR.exists():
    app.mount("/files", StaticFiles(directory=str(DELTA_TABLES_DIR)), name="files")


def _add_actions_to_dict(dt: DeltaTable) -> dict:
    result = dt.get_add_actions(flatten=True)
    try:
        return result.to_pydict()
    except AttributeError:
        return pa.RecordBatchReader.from_stream(result).read_all().to_pydict()


def _config():
    return load_config()


def _get_dt(share: str, schema: str, table: str) -> DeltaTable:
    config = _config()
    path = get_table_path(config, share, schema, table)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Table not found: {share}/{schema}/{table}")
    if isinstance(path, Path) and not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Delta table directory not found: {path}. Run ingestion first.",
        )
    storage_options = {"AWS_DEFAULT_REGION": AWS_REGION} if _S3_MODE else {}
    return DeltaTable(str(path), storage_options=storage_options or None)


def _presigned_url(s3_uri: str) -> str:
    """Generate a presigned GET URL for an S3 object URI."""
    import boto3
    parsed = urlparse(s3_uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    s3 = boto3.client("s3", region_name=AWS_REGION)
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=_PRESIGNED_URL_TTL,
    )


@app.get("/shares")
def list_shares():
    config = _config()
    return {"items": [{"name": s["name"]} for s in get_shares(config)]}


@app.get("/shares/{share}/schemas")
def list_schemas(share: str):
    config = _config()
    schemas = get_schemas(config, share)
    if not schemas and not any(s["name"] == share for s in get_shares(config)):
        raise HTTPException(status_code=404, detail=f"Share not found: {share}")
    return {"items": [{"name": sc["name"], "share": share} for sc in schemas]}


@app.get("/shares/{share}/schemas/{schema}/tables")
def list_tables(share: str, schema: str):
    config = _config()
    tables = get_tables(config, share, schema)
    return {
        "items": [
            {"name": t["name"], "schema": schema, "share": share}
            for t in tables
        ]
    }


@app.get("/shares/{share}/schemas/{schema}/tables/{table}/version")
def get_table_version(share: str, schema: str, table: str):
    dt = _get_dt(share, schema, table)
    return {"deltaTableVersion": dt.version()}


@app.get("/shares/{share}/schemas/{schema}/tables/{table}/metadata")
def get_table_metadata(share: str, schema: str, table: str, request: Request):
    dt = _get_dt(share, schema, table)
    arrow_schema = dt.schema().to_pyarrow()
    return JSONResponse(
        content={
            "protocol": {"minReaderVersion": 1},
            "metadata": {
                "id": f"{share}.{schema}.{table}",
                "name": table,
                "format": {"provider": "parquet"},
                "schemaString": arrow_schema.to_string(),
                "partitionColumns": [],
            },
        },
        headers={"Delta-Table-Version": str(dt.version())},
    )


# ── Tool proxy endpoints ────────────────────────────────────────────────────
# Called by the Next.js web app backend so it can execute tools without
# reimplementing DuckDB/parquet logic in Node.js.

from mcp_server.tools import list_tables as _list_tables_tool
from mcp_server.tools import get_schema as _get_schema_tool
from mcp_server.tools import sample_data as _sample_data_tool
from mcp_server.tools import query_table as _query_table_tool


@app.post("/tools/list_tables")
def tool_list_tables():
    return {"result": _list_tables_tool.run()}


@app.post("/tools/get_schema")
async def tool_get_schema(request: Request):
    body = await request.json()
    return {"result": _get_schema_tool.run(body["table_name"])}


@app.post("/tools/sample_data")
async def tool_sample_data(request: Request):
    body = await request.json()
    return {"result": _sample_data_tool.run(body["table_name"], body.get("n", 10))}


@app.post("/tools/query_table")
async def tool_query_table(request: Request):
    body = await request.json()
    return {"result": _query_table_tool.run(body["sql"])}


# ── Delta Sharing query endpoint ─────────────────────────────────────────────
@app.post("/shares/{share}/schemas/{schema}/tables/{table}/query")
def query_table(share: str, schema: str, table: str, request: Request):
    dt = _get_dt(share, schema, table)
    config = _config()
    table_path = get_table_path(config, share, schema, table)

    add_actions = _add_actions_to_dict(dt)
    parquet_paths = add_actions.get("path", [])

    if _S3_MODE:
        table_s3_uri = str(table_path).rstrip("/")
        files = [
            {
                "url": _presigned_url(f"{table_s3_uri}/{p}"),
                "id": p,
                "partitionValues": {},
                "size": 0,
                "stats": "",
            }
            for p in parquet_paths
        ]
    else:
        base_url = str(request.base_url).rstrip("/")
        table_rel = Path(table_path).relative_to(DELTA_TABLES_DIR)
        files = [
            {
                "url": f"{base_url}/files/{table_rel}/{p}",
                "id": p,
                "partitionValues": {},
                "size": 0,
                "stats": "",
            }
            for p in parquet_paths
        ]

    lines = (
        [json.dumps({"protocol": {"minReaderVersion": 1}})]
        + [json.dumps({"metaData": {"id": f"{share}.{schema}.{table}", "format": {"provider": "parquet"}}})]
        + [json.dumps({"file": f}) for f in files]
    )
    return JSONResponse(
        content={"lines": lines},
        headers={"Delta-Table-Version": str(dt.version())},
    )
