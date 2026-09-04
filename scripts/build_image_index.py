"""Build the image index: article_id (10-digit string) -> image path.

Scans the H&M image directory ONCE (filenames only — no image contents are
read) and writes a lightweight parquet index to
``serving_data/image_index.parquet`` with columns:

    article_id   str   canonical 10-digit id, e.g. "0800691008"
    image_path   str   absolute path of the image file
    extension    str   lowercase extension without dot, e.g. "jpg"

Memory-safe: iterates with os.scandir generators and accumulates plain
Python lists of strings (~105K rows), never loads image data.

Usage:
    python scripts/build_image_index.py
    IMAGE_DIR must be set (see .env.example), or pass --image-dir.
"""
import argparse
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import polars as pl

from backend.app.core.article_id import WIDTH, parse_article_id
from backend.app.core.config import get_settings

_NAME_RE = re.compile(r"^(\d{10})\.(jpg|jpeg|png|webp)$", re.IGNORECASE)


def scan_images(root: str) -> tuple[list[str], list[str], list[str], Counter, list[str]]:
    """One pass over the directory tree. Returns (ids, paths, exts, ext_counts, oddities)."""
    ids: list[str] = []
    paths: list[str] = []
    exts: list[str] = []
    ext_counts: Counter = Counter()
    oddities: list[str] = []

    for entry in os.scandir(root):
        if entry.is_file():
            oddities.append(f"top-level file: {entry.name}")
            continue
        if not entry.is_dir():
            continue
        prefix = entry.name
        for f in os.scandir(entry.path):
            if not f.is_file():
                oddities.append(f"non-file entry: {f.path}")
                continue
            m = _NAME_RE.match(f.name)
            if not m:
                oddities.append(f"non-conforming name: {f.path}")
                continue
            stem, ext = m.group(1), m.group(2).lower()
            # filename stem must equal the canonical id (guards against stray files)
            if stem != prefix + stem[3:]:
                oddities.append(f"stem does not match folder: {f.path}")
                continue
            v = parse_article_id(stem)
            if v is None or str(v).zfill(WIDTH) != stem:
                oddities.append(f"invalid article id: {f.path}")
                continue
            ids.append(stem)
            paths.append(f.path)
            exts.append(ext)
            ext_counts[ext] += 1
    return ids, paths, exts, ext_counts, oddities


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-dir", default=None, help="path to the H&M images folder")
    args = ap.parse_args()

    settings = get_settings()
    root = args.image_dir or (str(settings.image_dir) if settings.image_dir else None)
    if not root or not Path(root).exists():
        print(f"ERROR: image directory not found: {root!r}")
        print("Set IMAGE_DIR in .env or pass --image-dir.")
        return 1

    print(f"scanning {root} (filenames only)…")
    ids, paths, exts, ext_counts, oddities = scan_images(root)
    print(f"scanned in {time.time() - t0:.1f}s — {len(ids):,} images, extensions: {dict(ext_counts)}")
    if oddities:
        print(f"oddities ({len(oddities):,}, first 10): {oddities[:10]}")

    # duplicates: same canonical id mapped twice (e.g. .jpg + .png)
    seen: dict[str, int] = Counter(ids)
    dups = {k: v for k, v in seen.items() if v > 1}
    if dups:
        print(f"duplicate article ids in index: {len(dups)} — keeping the first occurrence")
        keep_first = set()
        f_ids, f_paths, f_exts = [], [], []
        for a, p, e in zip(ids, paths, exts):
            if a in keep_first:
                continue
            keep_first.add(a)
            f_ids.append(a)
            f_paths.append(p)
            f_exts.append(e)
        ids, paths, exts = f_ids, f_paths, f_exts

    out = settings.serving_data_dir / "image_index.parquet"
    settings.serving_data_dir.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame({"article_id": ids, "image_path": paths, "extension": exts}).sort("article_id")
    df.write_parquet(out, statistics=True)
    size_mb = out.stat().st_size / 1e6
    print(f"index written: {out} ({df.height:,} rows, {size_mb:.2f} MB, {time.time() - t0:.1f}s total)")

    # ---- coverage report vs the project's article dataset ----
    arts_file = settings.serving_data_dir / "articles_serving.parquet"
    if arts_file.exists():
        arts = pl.read_parquet(arts_file).select(
            pl.col("article_id").map_elements(format_id, return_dtype=pl.String).alias("article_id")
        )
        matched = arts.join(df.select("article_id"), on="article_id", how="semi").height
        total = arts.height
        print(f"\ncoverage: {matched:,}/{total:,} articles have images ({matched / total * 100:.1f}%)")
        print(f"missing images: {total - matched:,}")
        orphans = df.join(arts, on="article_id", how="anti").height
        print(f"images without a known article_id: {orphans:,}")
    return 0


def format_id(v: int) -> str:
    from backend.app.core.article_id import format_article_id

    return format_article_id(v)


if __name__ == "__main__":
    sys.exit(main())
