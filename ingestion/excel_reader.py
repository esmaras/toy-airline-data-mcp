"""
XLSX → list of (table_name, DataFrame) tuples.

Handles multi-sheet workbooks, column name cleaning, and basic type inference.
For large files (>100MB), tries python-calamine engine before openpyxl.
"""

import re
import time
from pathlib import Path

import pandas as pd

# Sheet slugs to skip during ingestion — these are metadata/legend tabs, not data.
# "s"  = Sources tab (22-32 rows × 2 cols, appears in every file)
SKIP_SHEETS: set[str] = {"s"}


def _slugify(text: str) -> str:
    """Convert arbitrary text to a clean snake_case identifier."""
    text = str(text).strip().lower()
    text = re.sub(r"[^\w\s]", "_", text)   # non-alphanumeric → underscore
    text = re.sub(r"[\s_]+", "_", text)     # collapse whitespace/underscores
    text = text.strip("_")
    return text or "col"


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to clean snake_case names, deduplicate if needed."""
    seen: dict[str, int] = {}
    new_cols = []
    for col in df.columns:
        name = _slugify(col)
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        new_cols.append(name)
    df.columns = new_cols
    return df


def _infer_types(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort type coercion: numeric and datetime columns."""
    for col in df.columns:
        if df[col].dtype == object:
            # Try datetime columns by name heuristic
            if any(kw in col for kw in ("date", "time", "dt", "year", "month")):
                try:
                    df[col] = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
                    continue
                except Exception:
                    pass
            # Try numeric
            converted = pd.to_numeric(df[col], errors="coerce")
            # Only apply if a meaningful fraction converted (avoids clobbering text)
            if converted.notna().sum() / max(len(df), 1) > 0.8:
                df[col] = converted
    return df


def _read_sheet(path: Path, sheet_name: str, engine: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name, engine=engine)
    df = _clean_columns(df)
    df = _infer_types(df)
    # Drop completely empty rows/columns
    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)
    return df


def read_excel_file(path: Path, file_size_bytes: int) -> list[tuple[str, pd.DataFrame]]:
    """
    Read all sheets from an XLSX file.

    Returns a list of (table_name, DataFrame) tuples.
    Table name: {file_stem}__{sheet_slug}  (or just {file_stem} if single sheet named 'Sheet1').
    """
    file_stem = _slugify(path.stem)
    large = file_size_bytes > 100 * 1024 * 1024  # 100MB

    # Choose engine: calamine is faster/lighter for large files
    engines_to_try = (["calamine", "openpyxl"] if large else ["openpyxl"])

    print(f"  Opening {path.name} ({file_size_bytes / 1e6:.1f} MB)...")
    if large:
        print(f"  [WARN] Large file — trying calamine engine first to reduce memory pressure")

    xl = None
    chosen_engine = None
    for engine in engines_to_try:
        try:
            xl = pd.ExcelFile(path, engine=engine)
            chosen_engine = engine
            break
        except Exception as exc:
            print(f"  [WARN] Engine '{engine}' failed: {exc}")

    if xl is None:
        raise RuntimeError(f"Could not open {path.name} with any available engine")

    sheet_names = xl.sheet_names
    print(f"  Sheets ({len(sheet_names)}): {sheet_names}  [engine={chosen_engine}]")

    results: list[tuple[str, pd.DataFrame]] = []
    for sheet in sheet_names:
        sheet_slug = _slugify(sheet)

        if sheet_slug in SKIP_SHEETS:
            print(f"    [{sheet}] skipped (in SKIP_SHEETS)")
            continue

        # Single sheet named generically → use just the file stem
        if len(sheet_names) == 1 and sheet_slug in ("sheet1", "sheet 1", file_stem):
            table_name = file_stem
        else:
            table_name = f"{file_stem}__{sheet_slug}"

        t0 = time.time()
        df = _read_sheet(path, sheet, chosen_engine)
        elapsed = time.time() - t0
        print(f"    [{sheet}] → {table_name}: {len(df):,} rows × {len(df.columns)} cols  ({elapsed:.1f}s)")
        results.append((table_name, df))

    return results
