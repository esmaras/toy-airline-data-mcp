"""
MCP tool: query_table
Execute SQL over tables served by the Delta Sharing server using DuckDB.

Reference tables by their short name (e.g. oag_may) — they are automatically
resolved to read_parquet([...urls...]) calls via the sharing server.

Default row cap is 100. Include LIMIT in your SQL for more (max 1000).

Example:
    SELECT origin, COUNT(*) as flights FROM oag_may GROUP BY origin ORDER BY flights DESC LIMIT 20
"""

import re

from mcp_server.delta_client import get_duckdb_conn, get_parquet_urls, list_all_tables, query_to_records
from mcp_server.tools._format import records_to_table

ROW_CAP = 1000
DEFAULT_CAP = 100


def _build_parquet_ref(table_name: str) -> str | None:
    try:
        urls = get_parquet_urls(table_name)
        if not urls:
            return None
        url_list = ", ".join(f"'{u}'" for u in urls)
        return f"read_parquet([{url_list}])"
    except Exception:
        return None


def _rewrite_table_refs(sql: str, known_tables: list[str]) -> str:
    for table_name in known_tables:
        ref = _build_parquet_ref(table_name)
        if ref is None:
            continue
        pattern = rf"\b{re.escape(table_name)}\b"
        sql = re.sub(pattern, ref, sql)
    return sql


def run(sql: str) -> str:
    if not sql.strip():
        return "No SQL provided."

    known = [t["name"] for t in list_all_tables() if "error" not in t]
    if not known:
        return "No tables available. Ensure the sharing server is running (make sharing-server)."

    rewritten_sql = _rewrite_table_refs(sql, known)

    has_limit = bool(re.search(r"\bLIMIT\b", sql, re.IGNORECASE))
    cap = ROW_CAP if has_limit else DEFAULT_CAP
    capped_sql = f"SELECT * FROM ({rewritten_sql}) _q LIMIT {cap}"

    try:
        con = get_duckdb_conn()
        records = query_to_records(capped_sql, con)
        con.close()
    except Exception as exc:
        return f"Query error: {exc}\n\nRewritten SQL:\n{rewritten_sql}"

    if not records:
        return "Query returned no rows."

    cap_note = (
        f"\n[Default cap: {DEFAULT_CAP} rows — add LIMIT to your SQL for more, up to {ROW_CAP}]"
        if not has_limit and len(records) == DEFAULT_CAP else ""
    )
    return f"{len(records)} row(s) returned:{cap_note}\n\n{records_to_table(records)}"
