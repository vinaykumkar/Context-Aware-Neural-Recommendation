"""DuckDB-backed access to optimized serving data.

The backend NEVER opens the ~800 MB source parquet dataset. All request-time
queries run against small serving parquet files (customer profiles, article
stats, per-customer history buckets and precomputed recommendation buckets).

Bucket files are opened directly by index (crc32(customer_id) % num_buckets),
so a lookup touches exactly one small file.
"""
from __future__ import annotations

import json
import logging
import threading
from functools import lru_cache

import duckdb

from ..core.config import Settings, get_settings
from ..core.serving import bucket_file, customer_bucket

logger = logging.getLogger("hm-recommender.store")


class StoreNotReady(RuntimeError):
    """Raised when required serving artifacts are missing/not built yet."""


_base_connection: duckdb.DuckDBPyConnection | None = None
_base_lock = threading.Lock()
_thread_local = threading.local()


def _create_base() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database=":memory:")
    con.execute("SET threads TO 4")
    s = get_settings()
    customers_file = s.serving_data_dir / "customers_serving.parquet"
    articles_file = s.serving_data_dir / "articles_serving.parquet"
    if customers_file.exists():
        con.execute(
            f"CREATE VIEW customers_serving AS SELECT * FROM read_parquet('{customers_file.as_posix()}')"
        )
    if articles_file.exists():
        con.execute(
            f"CREATE VIEW articles_serving AS SELECT * FROM read_parquet('{articles_file.as_posix()}')"
        )
    display_file = s.serving_data_dir / "articles_display.parquet"
    if display_file.exists():
        con.execute(
            f"CREATE VIEW articles_display AS SELECT * FROM read_parquet('{display_file.as_posix()}')"
        )
    pop_file = s.models_dir / "article_popularity.parquet"
    if pop_file.exists():
        con.execute(
            f"CREATE VIEW article_popularity AS SELECT * FROM read_parquet('{pop_file.as_posix()}')"
        )
    logger.info("duckdb store initialised (customers=%s, articles=%s)", customers_file.exists(), articles_file.exists())
    return con


def connection() -> duckdb.DuckDBPyConnection:
    """Thread-local cursor over one shared in-memory database.

    uvicorn runs sync endpoints in a threadpool; a single shared DuckDB
    connection is not safe for concurrent use, so every worker thread gets
    its own cursor (same database, sees the same views).
    """
    global _base_connection
    with _base_lock:
        if _base_connection is None:
            _base_connection = _create_base()
    cur = getattr(_thread_local, "cursor", None)
    if cur is None:
        cur = _base_connection.cursor()
        _thread_local.cursor = cur
    return cur


def require(customers: bool = False, articles: bool = False) -> None:
    s = get_settings()
    missing: list[str] = []
    if customers and not (s.serving_data_dir / "customers_serving.parquet").exists():
        missing.append("serving_data/customers_serving.parquet")
    if articles and not (s.serving_data_dir / "articles_serving.parquet").exists():
        missing.append("serving_data/articles_serving.parquet")
    if missing:
        raise StoreNotReady(
            "Serving data not built yet. Run `python scripts/build_serving_data.py`. Missing: " + ", ".join(missing)
        )


def history_bucket_path(customer_id: str, settings: Settings | None = None) -> str:
    s = settings or get_settings()
    b = customer_bucket(customer_id, s.num_buckets)
    p = bucket_file(s.history_dir, b)
    return p.as_posix()


def recs_bucket_path(customer_id: str, settings: Settings | None = None) -> str:
    s = settings or get_settings()
    b = customer_bucket(customer_id, s.num_buckets)
    p = bucket_file(s.recs_dir, b)
    return p.as_posix()


def query_history(customer_id: str, limit: int) -> list[dict]:
    """One small bucket file + article join; no source-dataset access."""
    con = connection()
    path = history_bucket_path(customer_id)
    rows = con.execute(
        f"""
        SELECT h.article_id, h.t_dat, h.price, h.sales_channel_id
        FROM read_parquet('{path}') h
        WHERE h.customer_id = ?
        ORDER BY h.t_dat DESC
        LIMIT {int(limit)}
        """,
        [customer_id],
    ).fetchall()
    return [
        {"article_id": r[0], "t_dat": str(r[1]), "price": r[2], "sales_channel_id": r[3]}
        for r in rows
    ]


def query_recommendations(customer_id: str, limit: int) -> list[dict]:
    con = connection()
    path = recs_bucket_path(customer_id)
    rows = con.execute(
        f"""
        SELECT article_id, rank, score, comp_collaborative, comp_content,
               comp_popularity, comp_repurchase, reason
        FROM read_parquet('{path}')
        WHERE customer_id = ?
        ORDER BY rank
        LIMIT {int(limit)}
        """,
        [customer_id],
    ).fetchall()
    return [
        {
            "article_id": r[0],
            "rank": r[1],
            "score": r[2],
            "comp_collaborative": r[3],
            "comp_content": r[4],
            "comp_popularity": r[5],
            "comp_repurchase": r[6],
            "reason": r[7],
        }
        for r in rows
    ]


def read_meta() -> dict:
    s = get_settings()
    out: dict = {}
    meta_file = s.serving_data_dir / "meta.json"
    if meta_file.exists():
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        out["dataset"] = data.get("dataset", data)
    recs_meta = s.models_dir / "build_recs_meta.json"
    if recs_meta.exists():
        out["recommendations"] = json.loads(recs_meta.read_text(encoding="utf-8"))
    nb_meta = s.models_dir / "build_neighbors_meta.json"
    if nb_meta.exists():
        out["neighbors"] = json.loads(nb_meta.read_text(encoding="utf-8"))
    return out
