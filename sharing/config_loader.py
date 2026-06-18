"""
Loads sharing_config.yaml and provides lookup helpers.

If the env var DELTA_TABLES_S3_PREFIX is set (e.g. s3://clearpath-data-lake-dev/delta/southwest_airline),
table locations are resolved as S3 URIs by replacing the leading "delta_tables" segment with that prefix.
Otherwise, paths are resolved relative to the project root (local dev mode).
"""

import os
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = Path(__file__).parent / "sharing_config.yaml"

# When set, table locations are rewritten to S3 URIs.
# Example: s3://clearpath-data-lake-dev/delta/southwest_airline
_S3_PREFIX = os.getenv("DELTA_TABLES_S3_PREFIX", "").rstrip("/")


def load_config() -> dict[str, Any]:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def get_shares(config: dict) -> list[dict]:
    return config.get("shares", [])


def get_schemas(config: dict, share_name: str) -> list[dict]:
    for share in config.get("shares", []):
        if share["name"] == share_name:
            return share.get("schemas", [])
    return []


def get_tables(config: dict, share_name: str, schema_name: str) -> list[dict]:
    for schema in get_schemas(config, share_name):
        if schema["name"] == schema_name:
            return schema.get("tables", [])
    return []


def get_table_path(config: dict, share_name: str, schema_name: str, table_name: str) -> str | Path | None:
    """
    Returns the table location as either:
    - A Path (local mode, no DELTA_TABLES_S3_PREFIX set)
    - A string S3 URI (when DELTA_TABLES_S3_PREFIX is set)
    """
    for table in get_tables(config, share_name, schema_name):
        if table["name"] == table_name:
            location = table["location"]
            if _S3_PREFIX:
                # Rewrite "delta_tables/some/path" → "s3://bucket/prefix/some/path"
                rel = location.removeprefix("delta_tables/")
                return f"{_S3_PREFIX}/{rel}"
            path = Path(location)
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            return path
    return None
