"""Inspect the source parquet datasets (metadata + samples, no full scans).

Usage:  python scripts/inspect_data.py
"""
import sys

from scripts._bootstrap import ROOT  # noqa: F401  (sys.path fix)

import glob
import json
from pathlib import Path

import pyarrow.parquet as pq

from backend.app.core.config import get_settings


def main() -> int:
    settings = get_settings()
    base = settings.data_dir
    if not base.exists():
        print(f"ERROR: data dir not found: {base}")
        return 1
    print(f"Source data dir: {base}\n")
    for ds in ("articles_model", "articles_display", "customers", "transactions"):
        files = sorted(glob.glob(str(base / ds / "part-*.parquet")))
        if not files:
            print(f"--- {ds}: NO PART FILES FOUND ---\n")
            continue
        pf = pq.ParquetFile(files[0])
        rows = sum(pq.ParquetFile(f).metadata.num_rows for f in files)
        size_mb = sum(Path(f).stat().st_size for f in files) / 1e6
        print(f"--- {ds} ---")
        print(f"  parts: {len(files)}   rows: {rows:,}   size: {size_mb:,.1f} MB")
        print("  schema:")
        for field in pf.schema_arrow:
            print(f"    {field.name}: {field.type}")
        sample = pq.read_table(files[0], columns=None).slice(0, 2).to_pylist()
        print("  sample rows:")
        for row in sample:
            print(f"    {json.dumps(row, default=str)[:220]}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
