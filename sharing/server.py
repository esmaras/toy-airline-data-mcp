"""
Local Delta Sharing REST server — FastAPI implementation.

Run:
    uvicorn sharing.server:app --host 0.0.0.0 --port 8080 --reload
"""

import json
from pathlib import Path

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

app = FastAPI(title="Southwest Airline Delta Sharing Server")

if DELTA_TABLES_DIR.exists():
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
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Delta table directory not found: {path}. Run ingestion first.",
        )
    return DeltaTable(str(path))


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


@app.post("/shares/{share}/schemas/{schema}/tables/{table}/query")
def query_table(share: str, schema: str, table: str, request: Request):
    dt = _get_dt(share, schema, table)
    config = _config()
    table_path = get_table_path(config, share, schema, table)

    add_actions = _add_actions_to_dict(dt)
    parquet_paths = add_actions.get("path", [])

    base_url = str(request.base_url).rstrip("/")
    table_rel = table_path.relative_to(DELTA_TABLES_DIR)

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
