PYTHON := venv/bin/python
PIP    := venv/bin/pip
PYTEST := venv/bin/pytest
UVICORN := venv/bin/uvicorn

SHARING_HOST := 0.0.0.0
SHARING_PORT := 8080
MCP_PORT     := 8081

# ──────────────────────────────────────────────────────────────────────────────
# Help (default target)
# ──────────────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "Southwest Toy Airline Data — available commands:"
	@echo ""
	@echo "  Setup"
	@echo "    make setup           Bootstrap venv and install all dependencies"
	@echo ""
	@echo "  Ingestion"
	@echo "    make dry-run         Enumerate XLSX sheets without writing Delta tables"
	@echo "    make ingest          Convert all XLSX → Delta tables in delta_tables/"
	@echo ""
	@echo "  Servers (both must run together)"
	@echo "    make sharing-server  Start the Delta Sharing REST server (port $(SHARING_PORT)) — terminal 1"
	@echo "    make mcp-server      Start the MCP server via stdio (for Claude Desktop) — terminal 2"
	@echo "    make mcp-server-sse  Start the MCP server via SSE HTTP (port $(MCP_PORT)) — terminal 2"
	@echo ""
	@echo "  Inspection"
	@echo "    make list-tables     List all Delta tables in delta_tables/"
	@echo "    make inspect-lounge  Preview lounge an sheet columns (before unpivot)"
	@echo "    make test            Run all tests"
	@echo ""

# ──────────────────────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────────────────────
.PHONY: setup
setup:
	@echo "==> Creating virtual environment..."
	python3 -m venv venv
	$(PIP) install --upgrade pip --quiet
	@echo "==> Installing dependencies..."
	$(PIP) install -r requirements.txt
	@echo "==> Installing DuckDB delta extension..."
	$(PYTHON) -c "import duckdb; c = duckdb.connect(); c.execute('INSTALL delta'); c.execute('LOAD delta'); print('    DuckDB delta extension ready.')"
	@echo "==> Verifying imports..."
	$(PYTHON) -c "import deltalake, duckdb, fastapi, mcp, pandas, pyarrow; print('    All core packages OK.')"
	@echo ""
	@echo "✓ Setup complete. Run 'make dry-run' to inspect your XLSX files."

# ──────────────────────────────────────────────────────────────────────────────
# Ingestion
# ──────────────────────────────────────────────────────────────────────────────
.PHONY: dry-run
dry-run:
	$(PYTHON) -m ingestion.ingest --dry-run

.PHONY: ingest
ingest:
	$(PYTHON) -m ingestion.ingest

# ──────────────────────────────────────────────────────────────────────────────
# Servers
# ──────────────────────────────────────────────────────────────────────────────
.PHONY: sharing-server
sharing-server:
	$(UVICORN) sharing.server:app \
		--host $(SHARING_HOST) \
		--port $(SHARING_PORT) \
		--reload

.PHONY: mcp-server
mcp-server:
	$(PYTHON) -m mcp_server.server --transport stdio

.PHONY: mcp-server-sse
mcp-server-sse:
	$(PYTHON) -m mcp_server.server --transport sse --port $(MCP_PORT)

# ──────────────────────────────────────────────────────────────────────────────
# Inspection
# ──────────────────────────────────────────────────────────────────────────────
.PHONY: list-tables
list-tables:
	$(PYTHON) -c "from mcp_server.tools.list_tables import run; print(run())"

.PHONY: inspect-lounge
inspect-lounge:
	$(PYTHON) -m ingestion.inspect

# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────
.PHONY: test
test:
	$(PYTEST) tests/ -v
