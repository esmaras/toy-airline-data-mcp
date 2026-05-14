"""
Southwest Airline Data — MCP Server

Exposes Delta Lake tables as MCP tools for LLM querying.

Tools:
  list_tables   — list all available tables
  get_schema    — column names and types for a table
  sample_data   — first N rows of a table
  query_table   — execute SQL via DuckDB

Run (stdio, for Claude Desktop):
    python -m mcp_server.server

Run (SSE, for HTTP-based clients):
    python -m mcp_server.server --transport sse --port 8081

Claude Desktop config:
    {
      "mcpServers": {
        "Toy Airline": {
          "command": "/your/path/to/toy-airline-data/venv/bin/python",
          "args": ["-m", "mcp_server.server"],
          "cwd": "/your/path/to/toy-airline-data",
          "env": { "PYTHONPATH": "/your/path/to/toy-airline-data" }
        }
      }
    }
"""

import argparse
import asyncio

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from mcp_server.tools import get_schema, list_tables, query_table, sample_data

app = Server("southwest-airline-data")

TOOLS = [
    Tool(
        name="list_tables",
        description="List all available Delta tables with schema and version info.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_schema",
        description="Return column names and data types for a specific Delta table.",
        inputSchema={
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "The name of the table (use list_tables to see available names).",
                }
            },
            "required": ["table_name"],
        },
    ),
    Tool(
        name="sample_data",
        description="Return the first N rows of a Delta table (default 10, max 100).",
        inputSchema={
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "The name of the table."},
                "n": {"type": "integer", "description": "Number of rows to return (default 10, max 100).", "default": 10},
            },
            "required": ["table_name"],
        },
    ),
    Tool(
        name="query_table",
        description=(
            "Execute a SQL query over Delta tables using DuckDB. "
            "Reference tables by their short name (e.g. SELECT * FROM oag_may LIMIT 5). "
            "Default cap is 100 rows — include LIMIT in SQL for more (max 1000)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SQL query to execute."}
            },
            "required": ["sql"],
        },
    ),
]


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "list_tables":
            result = list_tables.run()
        elif name == "get_schema":
            result = get_schema.run(arguments["table_name"])
        elif name == "sample_data":
            result = sample_data.run(arguments["table_name"], arguments.get("n", 10))
        elif name == "query_table":
            result = query_table.run(arguments["sql"])
        else:
            result = f"Unknown tool: {name}"
    except Exception as exc:
        result = f"Tool '{name}' raised an error: {exc}"

    return [TextContent(type="text", text=result)]


async def _run_stdio():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="southwest-airline-data",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main():
    parser = argparse.ArgumentParser(description="Southwest Airline Data MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()

    if args.transport == "stdio":
        asyncio.run(_run_stdio())
    else:
        try:
            from mcp.server.sse import SseServerTransport
            from starlette.applications import Starlette
            from starlette.routing import Route
            import uvicorn

            sse = SseServerTransport("/messages")

            async def handle_sse(request):
                async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                    await app.run(streams[0], streams[1], app.create_initialization_options())

            starlette_app = Starlette(routes=[Route("/sse", endpoint=handle_sse)])
            uvicorn.run(starlette_app, host="0.0.0.0", port=args.port)
        except ImportError as e:
            print(f"SSE transport requires additional dependencies: {e}")
            raise


if __name__ == "__main__":
    main()
