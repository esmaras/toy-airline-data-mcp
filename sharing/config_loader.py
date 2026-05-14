"""
Loads sharing_config.yaml and provides lookup helpers.
"""

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = Path(__file__).parent / "sharing_config.yaml"


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


def get_table_path(config: dict, share_name: str, schema_name: str, table_name: str) -> Path | None:
    for table in get_tables(config, share_name, schema_name):
        if table["name"] == table_name:
            location = table["location"]
            path = Path(location)
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            return path
    return None
