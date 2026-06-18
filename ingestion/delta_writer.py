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


def write_delta_table(table_name: str, df: pd.DataFrame, base_path: Path | str) -> str:
    """
    Write a DataFrame to a Delta table at base_path/table_name.

    base_path may be a local Path or an S3 URI string (e.g. s3://bucket/prefix).
    Uses mode='overwrite' so re-runs are idempotent.
    Returns the destination path/URI as a string.
    """
    if isinstance(base_path, str) and base_path.startswith("s3://"):
        dest = f"{base_path.rstrip('/')}/{table_name}"
        storage_options = {"AWS_DEFAULT_REGION": __import__("os").getenv("AWS_DEFAULT_REGION", "us-east-1")}
    else:
        dest_path = Path(base_path) / table_name
        dest_path.mkdir(parents=True, exist_ok=True)
        dest = str(dest_path)
        storage_options = {}

    df = _sanitize_object_columns(df)
    arrow_table = pa.Table.from_pandas(df, preserve_index=False)
    write_deltalake(dest, arrow_table, mode="overwrite", storage_options=storage_options or None)
    return dest
