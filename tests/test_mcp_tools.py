"""
Tests for MCP tools against real Delta tables.
Requires ingestion to have run first (delta_tables/ must exist).
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from ingestion.delta_writer import write_delta_table


@pytest.fixture
def sample_delta_table(tmp_path, monkeypatch):
    """Create a tiny Delta table and patch DELTA_TABLES_DIR to point at it."""
    df = pd.DataFrame({
        "origin": ["DAL", "HOU", "PHX", "LAS"],
        "destination": ["LAX", "DEN", "SEA", "SFO"],
        "flights": [150, 200, 80, 120],
    })
    write_delta_table("test_flights", df, tmp_path)

    import mcp_server.delta_client as dc
    monkeypatch.setattr(dc, "DELTA_TABLES_DIR", tmp_path)
    import mcp_server.tools.query_table as qt
    monkeypatch.setattr(qt, "DELTA_TABLES_DIR", tmp_path)
    import mcp_server.tools.sample_data as sd
    monkeypatch.setattr(sd, "DELTA_TABLES_DIR", tmp_path)

    return tmp_path


def test_list_tables(sample_delta_table):
    from mcp_server.tools.list_tables import run
    result = run()
    assert "test_flights" in result


def test_get_schema(sample_delta_table):
    from mcp_server.tools.get_schema import run
    result = run("test_flights")
    assert "origin" in result
    assert "flights" in result


def test_sample_data(sample_delta_table):
    from mcp_server.tools.sample_data import run
    result = run("test_flights", n=2)
    assert "DAL" in result or "HOU" in result


def test_query_table(sample_delta_table):
    from mcp_server.tools.query_table import run
    result = run("SELECT origin, flights FROM test_flights ORDER BY flights DESC LIMIT 2")
    assert "HOU" in result


def test_query_table_row_cap(sample_delta_table):
    from mcp_server.tools import query_table as qt_module
    original_cap = qt_module.ROW_CAP
    qt_module.ROW_CAP = 2
    try:
        from mcp_server.tools.query_table import run
        result = run("SELECT * FROM test_flights")
        assert "Capped at 2 rows" in result
    finally:
        qt_module.ROW_CAP = original_cap
