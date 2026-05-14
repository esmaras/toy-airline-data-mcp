# Southwest Toy Airline Data

A local data stack for querying Southwest Airlines public schedule, aircraft rotation, and fare data via an LLM. Built as a proof of concept.

**Stack:** XLSX → Delta Lake → Delta Sharing (REST) → MCP Server → LLM

---

## Prerequisites

- Python 3.12+
- The raw XLSX data files placed in `raw_data/` (not included in this repo)

---

## Setup

```zsh
# Clone the repo
git clone <repo-url>
cd toy-airline-data

# Add your XLSX files to raw_data/
# Expected files:
#   1_schedules_OAG_May.xlsx
#   1_schedules_OAG_Nov.xlsx
#   1a_schedules_WN_departures_and_arrivals.xlsx
#   1b_schedules_market_and_competition.xlsx
#   2_aircraft_rotation_FR24_Apr.xlsx
#   2a_aircraft_rotation_analysis.xlsx
#   3_fares_and_fare_analysis.xlsx

# Bootstrap the environment (creates venv/, installs deps, sets up DuckDB)
source setup-env.zsh
```

---

## Ingest Data

```zsh
# Preview what will be ingested (no writes)
make dry-run

# Convert all XLSX files → Delta tables in delta_tables/
make ingest
```

This produces 18 Delta tables in `delta_tables/`. The following files/sheets are intentionally excluded:

| Excluded | Reason |
|---|---|
| `1c_WN_lounge_analysis.xlsx` | Interactive Excel simulation model, not raw data |
| All `S` sheets | Sources/legend tabs (22-32 rows each) |

---

## Running the Servers

Two servers must run simultaneously. Open two terminal tabs:

**Terminal 1 — Delta Sharing Server** (port 8080)
```zsh
make sharing-server
```

**Terminal 2 — MCP Server** (stdio)
```zsh
make mcp-server
```

The MCP server reads all data through the sharing server — it does not access Delta tables directly.

---

## Available Data Tables

| Table | Description | Rows |
|---|---|---|
| `oag_may` | OAG schedule data — May 2026 | 188,722 |
| `oag_nov` | OAG schedule data — Nov 2026 | 190,649 |
| `oag_may_lists` | OAG reference lists (May) | 1,772 |
| `oag_nov_lists` | OAG reference lists (Nov) | 1,772 |
| `wn_departures_arrivals` | WN departure/arrival analysis | 181 |
| `market_competition_analysis` | Market & competition analysis | 47 |
| `market_seat_share` | Seat share tables | 244 |
| `market_tab` | Market summary table | 26 |
| `aircraft_list` | Aircraft fleet list | 201 |
| `rotation_fr24` | FlightRadar24 rotation data (Apr) | 12,611 |
| `rotation_lists` | Rotation reference lists | 1,502 |
| `rotation_analysis` | Aircraft rotation analysis | 233 |
| `rotation_tab` | Rotation summary table | 86 |
| `fare_analysis_1` | Fare analysis sheet 1 | 21 |
| `fare_analysis_2` | Fare analysis sheet 2 | 40 |
| `fare_analysis_3` | Fare analysis sheet 3 | 84 |
| `fare_chart_maker` | Fare chart source data | 42 |
| `fare_raw_data` | Raw fare data | 13,505 |

---

## Connecting to Claude Desktop

1. Open or create `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Add the following entry (adjust the path to match your clone location):

```json
{
  "mcpServers": {
    "Toy Airline": {
      "command": "/your/path/to/toy-airline-data/venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/your/path/to/toy-airline-data",
      "env": {
        "PYTHONPATH": "/your/path/to/toy-airline-data"
      }
    }
  }
}
```

3. Start the sharing server: `make sharing-server`

4. Restart Claude Desktop — the MCP server launches automatically as a subprocess.

5. In a new Claude chat, the following tools will be available:
   - `list_tables` — see all available tables
   - `get_schema` — column names and types for a table
   - `sample_data` — preview rows from a table
   - `query_table` — run SQL against the data

**Example prompts:**
- *"What tables are available?"*
- *"Show me the schema for the oag_may table"*
- *"What are the top 10 origin airports by flight count in May?"*
- *"Compare seat capacity between May and November for LAS"*

---

## Connecting to Other LLM Clients

The MCP server supports two transports:

### stdio (default)
Used by Claude Desktop and any MCP-compatible client that launches subprocesses. No extra config needed — the client manages the process lifecycle.

### SSE / HTTP
For clients that connect over HTTP (e.g. custom apps, other LLM frameworks):

```zsh
make mcp-server-sse   # starts on port 8081
```

Then point your client at `http://localhost:8081/sse`.

### Using with the Anthropic API directly

```python
import anthropic

client = anthropic.Anthropic()

response = client.beta.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    mcp_servers=[{
        "type": "url",
        "url": "http://localhost:8081/sse",
        "name": "toy-airline"
    }],
    messages=[{"role": "user", "content": "What tables are available?"}],
    betas=["mcp-client-2025-04-04"],
)
print(response.content)
```

### Using with other MCP-compatible frameworks

Any framework that implements the [Model Context Protocol](https://modelcontextprotocol.io) can connect to this server. The four tools exposed are:

| Tool | Input | Description |
|---|---|---|
| `list_tables` | _(none)_ | List all available tables |
| `get_schema` | `table_name: str` | Column names and types |
| `sample_data` | `table_name: str`, `n: int` (default 10) | First N rows |
| `query_table` | `sql: str` | SQL query (DuckDB dialect, 100-row default cap) |

SQL queries reference tables by short name — the server resolves them automatically:
```sql
SELECT origin, COUNT(*) as flights
FROM oag_may
GROUP BY origin
ORDER BY flights DESC
LIMIT 20
```

---

## All Commands

```zsh
make help            # show all commands
make setup           # create venv and install dependencies
make dry-run         # preview ingestion without writing
make ingest          # convert XLSX → Delta tables
make sharing-server  # start Delta Sharing REST server (port 8080)
make mcp-server      # start MCP server via stdio
make mcp-server-sse  # start MCP server via HTTP/SSE (port 8081)
make list-tables     # list all Delta tables
make inspect-lounge  # inspect the lounge analysis sheet structure
make test            # run tests
```

---

## Project Structure

```
toy-airline-data/
├── raw_data/           # XLSX source files (not in repo)
├── delta_tables/       # Generated Delta tables (not in repo)
├── ingestion/          # XLSX → Delta conversion scripts
├── sharing/            # Delta Sharing REST server (FastAPI) + client
├── mcp_server/         # MCP server + tools
├── tests/              # pytest test suite
├── Makefile            # All CLI commands
├── requirements.txt    # Python dependencies
└── setup-env.zsh       # One-time environment bootstrap
```
