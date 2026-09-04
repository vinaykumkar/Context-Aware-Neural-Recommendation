"""Stage 1b — Build the article DISPLAY serving table.

``parquet/articles_display`` holds the human-readable article metadata
(product type, group, colour, department…). This step projects it into a
compact serving file (``serving_data/articles_display.parquet``) used only
for website enrichment — the model keeps using its numeric features.

Output columns: article_id (numeric join key, Int64) + the display names.
The API serializes article_id as the canonical 10-digit string.

Usage:  python scripts/build_display.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import polars as pl

from backend.app.core.config import get_settings

DISPLAY_COLUMNS = [
    "product_type_name",
    "product_group_name",
    "graphical_appearance_name",
    "colour_group_name",
    "department_name",
    "index_name",
    "index_group_name",
    "section_name",
    "garment_group_name",
]


def main() -> int:
    t0 = time.time()
    settings = get_settings()
    src = settings.data_dir / "articles_display"
    if not src.exists():
        print(f"ERROR: {src} not found — nothing to build.")
        return 1

    files = [str(p) for p in sorted(src.glob("part-*.parquet"))]
    df = pl.read_parquet(files)
    n_raw = df.height
    df = df.unique(subset=["article_id"], keep="first")
    n_dupes = n_raw - df.height

    out = df.select(
        pl.col("article_id").cast(pl.Int64),
        *DISPLAY_COLUMNS,
    ).sort("article_id")

    settings.serving_data_dir.mkdir(parents=True, exist_ok=True)
    dest = settings.serving_data_dir / "articles_display.parquet"
    out.write_parquet(dest, statistics=True)
    size_mb = dest.stat().st_size / 1e6
    print(
        f"articles_display.parquet written: {out.height:,} rows, {size_mb:.2f} MB "
        f"({n_dupes} duplicate ids dropped, {time.time() - t0:.1f}s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
