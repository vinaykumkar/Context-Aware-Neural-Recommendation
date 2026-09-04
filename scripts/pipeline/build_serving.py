"""Stage 1 — Build optimized serving data from the (read-only) source parquet.

Outputs
-------
serving_data/articles_serving.parquet   article features + demand statistics
serving_data/customers_serving.parquet  customer profile summary + top categories
serving_data/history/bucket_XX.parquet  last N purchases per customer (hash-bucketed)
models/article_popularity.parquet       global + recency-decayed article popularity
serving_data/meta.json                  dataset facts + build metadata

Memory strategy: the ~32M-row transaction table is never loaded whole. It is
scanned lazily once per customer bucket (hash-partitioned slices), so every
operation works on small in-memory slices.
"""
from __future__ import annotations

import gc
import json
import sys
import time
import zlib
from pathlib import Path

import polars as pl

from scripts._bootstrap import ROOT  # noqa: F401  (sys.path fix)
from backend.app.core.config import get_settings
from backend.app.core.serving import bucket_file

FEATURE_COLS = [
    "product_type_name_index",
    "product_group_name_index",
    "graphical_appearance_name_index",
    "colour_group_name_index",
    "department_name_index",
    "index_name_index",
    "index_group_name_index",
    "section_name_index",
    "garment_group_name_index",
]

log_times: list[tuple[str, float]] = []


def log(msg: str, t0: float) -> None:
    now = time.time()
    log_times.append((msg, now - t0))
    print(f"[{now - t0:8.1f}s] {msg}", flush=True)


def articles_source_dir(settings) -> Path:
    """Model article data: articles_model (current layout) with legacy fallback."""
    model = Path(settings.data_dir, "articles_model")
    legacy = Path(settings.data_dir, "articles")
    return model if model.exists() else legacy


def load_articles(settings) -> pl.DataFrame:
    files = [str(p) for p in sorted(articles_source_dir(settings).glob("part-*.parquet"))]
    return pl.read_parquet(files).with_columns(pl.col("article_id").cast(pl.Int64))


def bucket_expr() -> pl.Expr:
    """crc32(customer_id) % num_buckets, matching backend/app/core/serving.py."""
    n = get_settings().num_buckets
    return (
        pl.col("customer_id")
        .map_elements(lambda s: zlib.crc32(s.encode("utf-8")), return_dtype=pl.UInt32)
        % n
    )


def load_customer_buckets(settings) -> pl.DataFrame:
    """customer_id -> (crc32 bucket, polars hash) used for fast semi-joins."""
    files = [str(p) for p in sorted(Path(settings.data_dir, "customers").glob("part-*.parquet"))]
    return (
        pl.scan_parquet(files)
        .select("customer_id")
        .with_columns(bucket_expr().alias("bucket"))
        .with_columns(pl.col("customer_id").hash().alias("ch"))
        .collect()
    )


def tx_slice_lazy(tx: pl.LazyFrame, ids: pl.DataFrame) -> pl.LazyFrame:
    """Transactions restricted to a set of customers via int-hash semi-join."""
    if "ch" not in ids.columns:
        ids = ids.with_columns(pl.col("customer_id").hash().alias("ch"))
    return (
        tx.with_columns(pl.col("customer_id").hash().alias("ch"))
        .join(ids.select("ch").lazy(), on="ch", how="semi")
    )


def tx_lazy(settings) -> pl.LazyFrame:
    files = [str(p) for p in sorted(Path(settings.data_dir, "transactions").glob("part-*.parquet"))]
    return pl.scan_parquet(files)


def build_article_serving(settings, articles: pl.DataFrame, tx: pl.LazyFrame, t0: float) -> pl.DataFrame:
    log("aggregating article demand statistics (streaming)…", t0)
    stats = (
        tx.group_by("article_id")
        .agg(
            pl.len().alias("purchase_count"),
            pl.col("price").mean().alias("avg_price"),
            pl.col("t_dat").min().alias("first_sale_date"),
            pl.col("t_dat").max().alias("last_sale_date"),
        )
        .collect(engine="streaming")
    )
    # unique customers per article: hash the id to int64 first (fast vectorized dedup)
    buyers = (
        tx.select("article_id", pl.col("customer_id").hash().alias("ch"))
        .unique()
        .group_by("article_id")
        .agg(pl.len().alias("unique_customers"))
        .collect(engine="streaming")
    )
    max_date = stats["last_sale_date"].max()
    recent = (
        tx.filter(pl.col("t_dat") > pl.lit(max_date) - pl.duration(days=84))
        .select("article_id", pl.col("customer_id").hash().alias("ch"))
        .unique()
        .group_by("article_id")
        .agg(pl.len().alias("customers_last_84d"))
        .collect(engine="streaming")
    )
    sales84 = (
        tx.filter(pl.col("t_dat") > pl.lit(max_date) - pl.duration(days=84))
        .group_by("article_id")
        .agg(pl.len().alias("sales_last_84d"))
        .collect(engine="streaming")
    )
    sales28 = (
        tx.filter(pl.col("t_dat") > pl.lit(max_date) - pl.duration(days=28))
        .group_by("article_id")
        .agg(pl.len().alias("sales_last_28d"))
        .collect(engine="streaming")
    )
    gc.collect()
    out = (
        articles.join(stats, on="article_id", how="left")
        .join(buyers, on="article_id", how="left")
        .join(sales84, on="article_id", how="left")
        .join(sales28, on="article_id", how="left")
        .join(recent, on="article_id", how="left")
        .with_columns(
            [pl.col(c).fill_null(0) for c in ("purchase_count", "unique_customers", "sales_last_84d", "customers_last_84d", "sales_last_28d")]
        )
        .sort("purchase_count", descending=True)
    )
    out.write_parquet(settings.serving_data_dir / "articles_serving.parquet", statistics=True)
    log(f"articles_serving.parquet written ({out.height:,} rows)", t0)
    return out


def build_customer_serving_and_history(settings, articles: pl.DataFrame, tx: pl.LazyFrame, t0: float) -> None:
    bucket_tbl = load_customer_buckets(settings)
    n_buckets = settings.num_buckets
    hist_limit = settings.history_per_customer

    profile_parts: list[pl.DataFrame] = []
    history_dir = settings.history_dir
    history_dir.mkdir(parents=True, exist_ok=True)

    for k in range(n_buckets):
        ids = bucket_tbl.filter(pl.col("bucket") == k)
        tx_slice = tx_slice_lazy(tx, ids).collect()
        if tx_slice.height == 0:
            (history_dir / f"bucket_{k:02d}.parquet").write_parquet(
                _empty_history_schema()
            )
            continue

        # --- purchase history: last N purchases per customer, newest first ---
        hist = (
            tx_slice.sort(["customer_id", "t_dat"], descending=[False, True])
            .group_by("customer_id", maintain_order=False)
            .head(hist_limit)
            .select("customer_id", "article_id", "t_dat", "price", "sales_channel_id")
            .sort(["customer_id", "t_dat"], descending=[False, True])
        )
        hist.write_parquet(bucket_file(history_dir, k), statistics=True)

        # --- customer category affinities (counts over encoded features) ---
        enriched = tx_slice.join(articles, on="article_id", how="left")
        agg = enriched.group_by("customer_id").agg(
            pl.col("t_dat").min().alias("first_purchase_date"),
            pl.col("t_dat").max().alias("last_purchase_date"),
            *[pl.col(c).mode().first().alias(f"top_{c.removesuffix('_name_index')}") for c in FEATURE_COLS],
        )
        prof = ids.join(agg, on="customer_id", how="left").with_columns(pl.lit(k).alias("bucket"))
        profile_parts.append(prof)
        log(f"bucket {k:02d}/{n_buckets}: history={hist.height:,} rows, customers={prof.height:,}", t0)
        del tx_slice, hist, enriched, agg

    customers_serving = pl.concat(profile_parts, how="vertical").sort("customer_id")
    # Enrich with source customer attributes
    src = pl.read_parquet([str(p) for p in sorted(Path(settings.data_dir, "customers").glob("part-*.parquet"))])
    customers_serving = customers_serving.join(
        src, on="customer_id", how="left", validate="1:1"
    )
    # Mark customers that have at least one transaction (source includes all members)
    customers_serving = customers_serving.with_columns(
        pl.col("last_purchase_date").is_not_null().alias("has_purchases")
    )
    customers_serving.write_parquet(settings.serving_data_dir / "customers_serving.parquet", statistics=True)
    log(f"customers_serving.parquet written ({customers_serving.height:,} rows)", t0)


def _empty_history_schema() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "customer_id": pl.String,
            "article_id": pl.Int64,
            "t_dat": pl.Date,
            "price": pl.Float64,
            "sales_channel_id": pl.Int32,
        }
    )


def build_popularity(settings, articles_serving: pl.DataFrame, t0: float) -> pl.DataFrame:
    log("building popularity model…", t0)
    pop = articles_serving.select(
        "article_id",
        "purchase_count",
        "unique_customers",
        "sales_last_84d",
        "sales_last_28d",
        "last_sale_date",
        # Blended popularity: log-scaled total demand + recent demand bonus
        (
            0.4 * (pl.col("purchase_count").log1p() / pl.col("purchase_count").log1p().max())
            + 0.6 * (pl.col("sales_last_84d").log1p() / pl.col("sales_last_84d").log1p().max())
        ).alias("popularity_score"),
    ).with_columns(
        pl.col("popularity_score").rank("ordinal", descending=True).alias("popularity_rank")
    )
    pop.write_parquet(settings.models_dir / "article_popularity.parquet", statistics=True)
    log(f"article_popularity.parquet written ({pop.height:,} rows)", t0)
    return pop


def write_meta(settings, articles_serving: pl.DataFrame, t0: float) -> None:
    tx = tx_lazy(settings)
    stats = tx.select(
        pl.len().alias("n_transactions"),
        pl.col("t_dat").min().alias("min_date"),
        pl.col("t_dat").max().alias("max_date"),
        pl.col("customer_id").n_unique().alias("n_active_customers"),
        pl.col("article_id").n_unique().alias("n_purchased_articles"),
    ).collect(engine="streaming").row(0, named=True)
    meta = {
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pipeline_version": "1.0.0",
        "dataset": {
            **stats,
            "min_date": str(stats["min_date"]),
            "max_date": str(stats["max_date"]),
            "n_articles": articles_serving.height,
            "total_seconds": round(sum(d for _, d in log_times), 1),
        },
        "serving": {
            "num_buckets": settings.num_buckets,
            "history_per_customer": settings.history_per_customer,
        },
        "stage_timings": [{"stage": m, "seconds": round(d, 1)} for m, d in log_times],
    }
    (settings.serving_data_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    log(f"meta.json written — dataset: {json.dumps(meta['dataset'])}", t0)


def main() -> int:
    t0 = time.time()
    settings = get_settings()
    settings.ensure_dirs()
    print("=== Stage 1: serving data ===", flush=True)
    articles = load_articles(settings)
    log(f"articles loaded ({articles.height:,})", t0)
    tx = tx_lazy(settings)
    articles_serving = build_article_serving(settings, articles, tx, t0)
    build_customer_serving_and_history(settings, articles, tx, t0)
    build_popularity(settings, articles_serving, t0)
    write_meta(settings, articles_serving, t0)
    log("stage 1 complete", t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
