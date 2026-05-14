"""
MCP data access layer — reads via the Delta Sharing server, queries via DuckDB.

All data access goes through the sharing server (http://localhost:8080).
DuckDB is used only as a query engine pointed at the parquet URLs the
sharing server returns — it does not read Delta tables directly.

Both servers must be running:
    make sharing-server   (terminal 1)
    make mcp-server       (terminal 2)
"""

from typing import Any

import duckdb

from sharing.client import (
    find_table,
    get_table_metadata,
    get_table_parquet_urls,
    get_table_version,
    list_all_tables as _sharing_list_tables,
)


def list_all_tables() -> list[dict[str, Any]]:
    """List all tables from the sharing server."""
    try:
        tables = _sharing_list_tables()
    except RuntimeError as exc:
        return [{"name": "ERROR", "error": str(exc)}]

    result = []
    for t in tables:
        try:
            version = get_table_version(t["share"], t["schema"], t["name"])
            result.append({
                "name": t["name"],
                "schema": t["schema"],
                "share": t["share"],
                "version": version,
                "row_count": None,
                "num_files": None,
            })
        except Exception as exc:
            result.append({"name": t["name"], "error": str(exc)})
    return result


def get_table_schema_str(table_name: str) -> str:
    t = find_table(table_name)
    if t is None:
        raise ValueError(f"Table '{table_name}' not found in sharing server.")
    meta = get_table_metadata(t["share"], t["schema"], table_name)
    return meta.get("metadata", {}).get("schemaString") or str(meta)


def get_duckdb_conn() -> duckdb.DuckDBPyConnection:
    """Return a plain DuckDB connection (no delta extension needed — using parquet URLs)."""
    return duckdb.connect()


def get_parquet_urls(table_name: str) -> list[str]:
    """Fetch parquet file URLs for a table from the sharing server."""
    t = find_table(table_name)
    if t is None:
        raise ValueError(f"Table '{table_name}' not found in sharing server.")
    return get_table_parquet_urls(t["share"], t["schema"], table_name)


def query_to_records(sql: str, con: duckdb.DuckDBPyConnection | None = None) -> list[dict[str, Any]]:
    """Execute SQL and return results as a list of dicts."""
    close_after = con is None
    if con is None:
        con = get_duckdb_conn()
    try:
        result = con.execute(sql).fetchdf()
        return result.to_dict(orient="records")
    finally:
        if close_after:
            con.close()
