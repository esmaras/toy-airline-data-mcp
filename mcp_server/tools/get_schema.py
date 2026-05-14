"""
MCP tool: get_schema
Returns column names and data types for a given table via the sharing server.
"""

from mcp_server.delta_client import get_parquet_urls, get_duckdb_conn, query_to_records


def run(table_name: str) -> str:
    try:
        urls = get_parquet_urls(table_name)
    except ValueError as exc:
        return str(exc)

    if not urls:
        return f"No parquet files found for '{table_name}'."

    url_list = ", ".join(f"'{u}'" for u in urls)
    sql = f"DESCRIBE SELECT * FROM read_parquet([{url_list}]) LIMIT 0"
    try:
        con = get_duckdb_conn()
        records = query_to_records(sql, con)
        con.close()
    except Exception as exc:
        return f"Error reading schema for '{table_name}': {exc}"

    lines = [f"Schema for '{table_name}':\n"]
    for row in records:
        col_name = row.get("column_name", "")
        col_type = row.get("column_type", "")
        lines.append(f"  {col_name:<40} {col_type}")
    return "\n".join(lines)
