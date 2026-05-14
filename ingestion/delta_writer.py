"""
DataFrame → Delta table writer using deltalake (delta-rs, no Spark/JVM).
"""

import datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
from deltalake import write_deltalake


def _sanitize_object_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Coerce object-dtype columns that contain non-string types into strings.

    PyArrow fails on object columns with mixed types (e.g. str+int, str+datetime.time).
    Strategy: for each object column, if any non-null value is not a plain str,
    convert the whole column to str (preserving NaN as None).
    """
    for col in df.columns:
        if df[col].dtype != object:
            continue
        non_null = df[col].dropna()
        if non_null.empty:
            continue
        if not all(isinstance(v, str) for v in non_null):
            df[col] = df[col].apply(
                lambda v: None if pd.isna(v) else (
                    v.strftime("%H:%M:%S") if isinstance(v, datetime.time) else str(v)
                )
            )
    return df


def write_delta_table(table_name: str, df: pd.DataFrame, base_path: Path) -> Path:
    """
    Write a DataFrame to a Delta table at base_path/table_name.

    Uses mode='overwrite' so re-runs are idempotent.
    Returns the path written to.
    """
    dest = base_path / table_name
    dest.mkdir(parents=True, exist_ok=True)

    df = _sanitize_object_columns(df)

    arrow_table = pa.Table.from_pandas(df, preserve_index=False)
    write_deltalake(str(dest), arrow_table, mode="overwrite")
    return dest
