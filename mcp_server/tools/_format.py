"""
Shared output formatter for MCP tool results.
Produces compact pipe-delimited tables instead of JSON to minimize token usage.
"""

MAX_CELL_LEN = 50  # truncate long string values


def _fmt(value) -> str:
    if value is None:
        return ""
    s = str(value)
    if len(s) > MAX_CELL_LEN:
        s = s[:MAX_CELL_LEN - 1] + "…"
    return s


def records_to_table(records: list[dict]) -> str:
    if not records:
        return "(no rows)"

    headers = list(records[0].keys())
    rows = [[_fmt(row.get(h)) for h in headers] for row in records]

    # Column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(cells):
        return " | ".join(c.ljust(widths[i]) for i, c in enumerate(cells))

    separator = "-+-".join("-" * w for w in widths)
    lines = [fmt_row(headers), separator] + [fmt_row(row) for row in rows]
    return "\n".join(lines)
