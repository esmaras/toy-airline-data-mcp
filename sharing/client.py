"""
Delta Sharing client — talks to the local sharing server over HTTP.
Used by the MCP server instead of reading Delta tables directly.

The sharing server must be running at SHARING_SERVER_URL before the MCP server
can serve requests.
"""

import json
from typing import Any

import httpx

SHARING_SERVER_URL = "http://localhost:8080"
TIMEOUT = 10.0


def _get(path: str) -> dict:
    url = f"{SHARING_SERVER_URL}{path}"
    response = httpx.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def _post(path: str, body: dict | None = None) -> dict:
    url = f"{SHARING_SERVER_URL}{path}"
    response = httpx.post(url, json=body or {}, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def list_all_tables() -> list[dict[str, Any]]:
    """Walk shares → schemas → tables via the sharing server."""
    try:
        shares_data = _get("/shares")
    except httpx.ConnectError:
        raise RuntimeError(
            f"Cannot connect to Delta Sharing server at {SHARING_SERVER_URL}. "
            "Run 'make sharing-server' first."
        )

    tables = []
    for share in shares_data.get("items", []):
        share_name = share["name"]
        schemas_data = _get(f"/shares/{share_name}/schemas")
        for schema in schemas_data.get("items", []):
            schema_name = schema["name"]
            tables_data = _get(f"/shares/{share_name}/schemas/{schema_name}/tables")
            for table in tables_data.get("items", []):
                tables.append({
                    "share": share_name,
                    "schema": schema_name,
                    "name": table["name"],
                })
    return tables


def get_table_version(share: str, schema: str, table: str) -> int:
    data = _get(f"/shares/{share}/schemas/{schema}/tables/{table}/version")
    return data.get("deltaTableVersion", 0)


def get_table_metadata(share: str, schema: str, table: str) -> dict:
    return _get(f"/shares/{share}/schemas/{schema}/tables/{table}/metadata")


def get_table_parquet_urls(share: str, schema: str, table: str) -> list[str]:
    """Return parquet file URLs for a table from the sharing server."""
    data = _post(f"/shares/{share}/schemas/{schema}/tables/{table}/query")
    urls = []
    for line in data.get("lines", []):
        obj = json.loads(line) if isinstance(line, str) else line
        if "file" in obj:
            urls.append(obj["file"]["url"])
    return urls


def find_table(table_name: str) -> dict | None:
    """Find a table by its short name across all shares/schemas."""
    for t in list_all_tables():
        if t["name"] == table_name:
            return t
    return None
