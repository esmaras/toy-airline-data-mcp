"""
Main ingestion entry point: converts all XLSX files in raw_data/ → Delta tables.

Usage:
    python -m ingestion.ingest            # full run
    python -m ingestion.ingest --dry-run  # enumerate sheets only, no writes
"""

import argparse
import time
from pathlib import Path

from ingestion.delta_writer import write_delta_table
from ingestion.excel_reader import read_excel_file

PROJECT_ROOT = Path(__file__).parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "raw_data"
DELTA_TABLES_DIR = PROJECT_ROOT / "delta_tables"

# Files to skip entirely — complex Excel dashboards/models, not raw data tables.
# The lounge analysis is a formula-driven simulation derived from OAG schedule data.
SKIP_FILES: set[str] = {"1c_WN_lounge_analysis.xlsx"}


def run(dry_run: bool = False) -> None:
    xlsx_files = sorted(RAW_DATA_DIR.glob("*.xlsx"))
    if not xlsx_files:
        print(f"No XLSX files found in {RAW_DATA_DIR}")
        return

    print(f"Found {len(xlsx_files)} XLSX file(s) in {RAW_DATA_DIR}\n")

    if not dry_run:
        DELTA_TABLES_DIR.mkdir(exist_ok=True)

    total_tables = 0
    for xlsx_path in xlsx_files:
        if xlsx_path.name.startswith("~$"):
            # Excel lock file — created when a file is open in Excel, not real data
            continue

        if xlsx_path.name in SKIP_FILES:
            print(f"Skipping: {xlsx_path.name}  (in SKIP_FILES)\n")
            continue

        file_size = xlsx_path.stat().st_size
        print(f"{'[DRY-RUN] ' if dry_run else ''}Processing: {xlsx_path.name}")

        t_file_start = time.time()
        try:
            sheets = read_excel_file(xlsx_path, file_size)
        except Exception as exc:
            print(f"  [ERROR] Failed to read {xlsx_path.name}: {exc}\n")
            continue

        for table_name, df in sheets:
            if dry_run:
                print(f"    Would write → delta_tables/{table_name}  ({len(df):,} rows)")
            else:
                dest = write_delta_table(table_name, df, DELTA_TABLES_DIR)
                print(f"    Written → {dest.relative_to(PROJECT_ROOT)}")
            total_tables += 1

        elapsed = time.time() - t_file_start
        print(f"  Done in {elapsed:.1f}s\n")

    print(f"{'[DRY-RUN] ' if dry_run else ''}Finished. {total_tables} table(s) {'would be ' if dry_run else ''}written.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest XLSX files into Delta Lake tables")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Enumerate sheets and rows without writing Delta tables",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
