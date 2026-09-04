"""Serving-layout helpers shared by the offline pipeline and the backend.

The huge per-customer tables (purchase history, precomputed recommendations)
are hash-partitioned into a fixed number of parquet bucket files. A single
customer's data therefore lives in exactly one small file, which the backend
can open directly — no full-table scans at request time.

IMPORTANT: ``customer_bucket`` is a stable hash (crc32) that must never
change, otherwise bucket files written by the pipeline would point to the
wrong location for the backend.
"""
from __future__ import annotations

import zlib
from pathlib import Path

from .config import Settings, get_settings


def customer_bucket(customer_id: str, num_buckets: int | None = None) -> int:
    """Stable bucket index for a customer id (crc32, UTF-8 bytes)."""
    n = num_buckets if num_buckets is not None else get_settings().num_buckets
    return zlib.crc32(customer_id.encode("utf-8")) % n


def bucket_file(directory: Path, bucket: int) -> Path:
    return directory / f"bucket_{bucket:02d}.parquet"


def bucket_glob(directory: Path) -> str:
    return str(directory / "bucket_*.parquet")


def bucket_paths(directory: Path, settings: Settings | None = None) -> list[Path]:
    s = settings or get_settings()
    return [bucket_file(directory, b) for b in range(s.num_buckets)]


def serving_status(settings: Settings | None = None) -> dict:
    """Report which serving artifacts exist (used by /health and startup checks)."""
    s = settings or get_settings()
    def _exists(p: Path) -> bool:
        return p.exists()
    return {
        "data_dir": str(s.data_dir),
        "data_dir_present": _exists(s.data_dir),
        "customers_serving": _exists(s.serving_data_dir / "customers_serving.parquet"),
        "articles_serving": _exists(s.serving_data_dir / "articles_serving.parquet"),
        "popularity": _exists(s.models_dir / "article_popularity.parquet"),
        "history_buckets": sum(1 for p in bucket_paths(s.history_dir, s) if _exists(p)),
        "recommendation_buckets": sum(1 for p in bucket_paths(s.recs_dir, s) if _exists(p)),
        "num_buckets": s.num_buckets,
        "model_meta": _exists(s.models_dir / "model_meta.json"),
    }
