"""
Inspect the lounge analysis `an` sheet to determine its column structure
before committing to an unpivot (melt) strategy.

Reads only headers + first 3 rows — fast, no Delta write.

Usage:
    python -m ingestion.inspect
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
LOUNGE_FILE = PROJECT_ROOT / "raw_data" / "1c_WN_lounge_analysis.xlsx"
SHEET_NAME = "an"
PREVIEW_COLS = 10  # how many columns to show at start and end


def run() -> None:
    if not LOUNGE_FILE.exists():
        print(f"File not found: {LOUNGE_FILE}")
        return

    size_mb = LOUNGE_FILE.stat().st_size / 1e6
    print(f"Inspecting: {LOUNGE_FILE.name} ({size_mb:.1f} MB), sheet='{SHEET_NAME}'")
    print("Reading headers + 3 rows via calamine...\n")

    df = pd.read_excel(LOUNGE_FILE, sheet_name=SHEET_NAME, engine="calamine", nrows=3)

    total_cols = len(df.columns)
    total_rows_note = "~60,591 (from dry-run)"

    print(f"Total columns : {total_cols}")
    print(f"Total rows    : {total_rows_note}")
    print()

    first_cols = list(df.columns[:PREVIEW_COLS])
    print(f"First {PREVIEW_COLS} columns:")
    for i, col in enumerate(first_cols):
        sample_vals = df[col].tolist()
        print(f"  [{i:>4}] {col!r:<50}  sample: {sample_vals}")

    print()

    last_cols = list(df.columns[-PREVIEW_COLS:])
    print(f"Last {PREVIEW_COLS} columns:")
    for i, col in enumerate(last_cols, start=total_cols - PREVIEW_COLS):
        sample_vals = df[col].tolist()
        print(f"  [{i:>4}] {col!r:<50}  sample: {sample_vals}")

    print()
    print("--- Guidance ---")
    print("ID columns are the ones that identify each row (e.g. market, carrier, route).")
    print("Value columns are the ones that will be pivoted (e.g. airport codes, time periods).")
    print("Look at the first few columns — they are likely the ID columns.")
    print()
    print("Once you identify the ID columns, share them and we will implement the melt.")


if __name__ == "__main__":
    run()
