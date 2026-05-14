"""
MCP tool: list_tables
Returns all tables available via the Delta Sharing server.
"""

from mcp_server.delta_client import list_all_tables


def run() -> str:
    tables = list_all_tables()
    if not tables:
        return "No tables found. Ensure the sharing server is running (make sharing-server)."

    if len(tables) == 1 and "error" in tables[0]:
        return f"Error connecting to sharing server: {tables[0]['error']}"

    lines = [f"Found {len(tables)} table(s):\n"]
    for t in tables:
        if "error" in t:
            lines.append(f"  - {t['name']}  [ERROR: {t['error']}]")
        else:
            lines.append(f"  - {t['name']}  (schema={t['schema']}, version={t['version']})")
    return "\n".join(lines)
