"""
MCP tool: sample_data
Returns the first N rows of a table via the sharing server.
"""

from mcp_server.delta_client import get_parquet_urls, get_duckdb_conn, query_to_records
from mcp_server.tools._format import records_to_table


def run(table_name: str, n: int = 10) -> str:
    n = min(n, 100)
    try:
        urls = get_parquet_urls(table_name)
    except ValueError as exc:
        return str(exc)

    if not urls:
        return f"No parquet files found for '{table_name}'."

    url_list = ", ".join(f"'{u}'" for u in urls)
    sql = f"SELECT * FROM read_parquet([{url_list}]) LIMIT {n}"
    try:
        con = get_duckdb_conn()
        records = query_to_records(sql, con)
        con.close()
    except Exception as exc:
        return f"Error sampling '{table_name}': {exc}"

    if not records:
        return f"Table '{table_name}' is empty."

    return f"First {len(records)} row(s) from '{table_name}':\n\n{records_to_table(records)}"
