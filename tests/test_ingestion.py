"""
Tests for the ingestion layer.
Uses in-memory DataFrames — does not require actual XLSX files.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from ingestion.excel_reader import _clean_columns, _slugify
from ingestion.delta_writer import write_delta_table


def test_slugify_basic():
    assert _slugify("Flight Date") == "flight_date"
    assert _slugify("  Origin/Dest  ") == "origin_dest"
    assert _slugify("123") == "123"


def test_clean_columns_deduplication():
    df = pd.DataFrame(columns=["Name", "name", "NAME"])
    df = _clean_columns(df)
    assert df.columns.tolist() == ["name", "name_1", "name_2"]


def test_clean_columns_special_chars():
    df = pd.DataFrame(columns=["Flight #", "Dep. Time", "Rev ($)"])
    df = _clean_columns(df)
    for col in df.columns:
        assert col.islower()
        assert " " not in col


def test_write_delta_table_creates_delta_log():
    df = pd.DataFrame({"origin": ["DAL", "HOU"], "flights": [100, 200]})
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        write_delta_table("test_table", df, base)
        assert (base / "test_table" / "_delta_log").exists()


def test_write_delta_table_idempotent():
    df = pd.DataFrame({"a": [1, 2, 3]})
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        write_delta_table("idempotent_table", df, base)
        write_delta_table("idempotent_table", df, base)
        from deltalake import DeltaTable
        dt = DeltaTable(str(base / "idempotent_table"))
        assert dt.version() >= 1
