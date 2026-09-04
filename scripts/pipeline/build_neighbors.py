"""Stage 2 — Item-to-item similarity models.

Two neighbor tables are produced (top-K most similar items per article):

* ``models/item_neighbors_collab.parquet``  — behavioral similarity from
  co-purchase patterns. Pairs are weighted by exponential time decay
  (half-life 90 days), then cosine-normalized:
  ``score(i, j) = w_ij / sqrt(d_i * d_j)`` where ``d_i`` is the weighted
  purchase degree of item i. Score 1.0 = identical purchase profiles.
* ``models/item_neighbors_content.parquet`` — attribute similarity from the
  9 encoded article features (one-hot cosine).
* ``models/article_onehot.npz`` + ``models/feature_layout.json`` — one-hot
  article vectors used by the recommendation generator and explainability.

Memory strategy: sparse scipy matrices, blockwise similarity computation,
never materializing the full 105K x 105K matrix.
"""
from __future__ import annotations

import gc
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
import scipy.sparse as sp

from scripts._bootstrap import ROOT  # noqa: F401  (sys.path fix)
from backend.app.core.config import get_settings
from scripts.pipeline.build_serving import bucket_expr, load_customer_buckets, tx_lazy, tx_slice_lazy

HALF_LIFE_DAYS = 90.0
TOP_K = 150
BLOCK = 1024
# No absolute cosine floor: popular items have large weighted degrees, so
# genuine co-purchase cosines can be ~1e-4. Neighbor quality comes from the
# top-K ranking, not from an absolute floor. MIN_COWEIGHT only removes
# single stale co-purchases.
MIN_COSINE = 0.0
MIN_COWEIGHT = 0.02

log_times: list[tuple[str, float]] = []


def log(msg: str, t0: float) -> None:
    now = time.time()
    log_times.append((msg, now - t0))
    print(f"[{now - t0:8.1f}s] {msg}", flush=True)


def build_weighted_pairs(settings, tx: pl.LazyFrame, articles: pl.DataFrame, t0: float) -> pl.DataFrame:
    """Unique (customer, article) pairs with summed exponential decay weight.

    Processed one customer bucket at a time; pairs are customer-unique so
    bucket slices never need merging across buckets. Each bucket is reduced
    to compact (user_idx, item_idx, w) int/float columns immediately — full
    64-char customer ids never accumulate across buckets.
    """
    max_date = tx.select(pl.col("t_dat").max()).collect().item()
    art_map = articles.select(
        "article_id",
        pl.int_range(0, articles.height, dtype=pl.Int32).alias("item_idx"),
    )
    # global user index: customer_id -> user_idx (+ int hash for fast joins)
    customers = pl.scan_parquet(
        [str(p) for p in sorted((settings.data_dir / "customers").glob("part-*.parquet"))]
    ).select("customer_id")
    user_map = customers.with_row_index("user_idx").with_columns(
        pl.col("user_idx").cast(pl.Int32),
        pl.col("customer_id").hash().alias("ch"),
    ).collect()
    bucket_tbl = load_customer_buckets(settings)
    tmp_dir = settings.models_dir / "tmp_pairs"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for k in range(settings.num_buckets):
        out_file = tmp_dir / f"bucket_{k:02d}.parquet"
        if out_file.exists():
            log(f"pairs bucket {k:02d}/{settings.num_buckets} (cached)", t0)
            continue
        ids = bucket_tbl.filter(pl.col("bucket") == k)
        pairs = (
            tx_slice_lazy(tx, ids)
            .with_columns(
                (0.5 ** ((pl.lit(max_date) - pl.col("t_dat")).dt.total_days() / HALF_LIFE_DAYS)).alias("w")
            )
            .group_by("customer_id", "article_id")
            .agg(pl.col("w").sum())
            .collect()
            .join(art_map, on="article_id", how="inner")
            .drop("article_id")
            .with_columns(pl.col("customer_id").hash().alias("ch"))
            .join(user_map.select("ch", "user_idx"), on="ch", how="inner")
            .drop("customer_id", "ch")
            .select("user_idx", "item_idx", "w")
        )
        pairs.write_parquet(out_file)
        del pairs
        gc.collect()
        log(f"pairs bucket {k:02d}/{settings.num_buckets}", t0)

    parts = [pl.read_parquet(p) for p in sorted(tmp_dir.glob("bucket_*.parquet"))]
    pairs = pl.concat(parts, how="vertical").sort("user_idx")
    del parts
    gc.collect()
    log(f"weighted pairs: {pairs.height:,}", t0)
    return pairs


def pairs_to_csc(pairs: pl.DataFrame, n_items: int, t0: float) -> sp.csc_matrix:
    """Canonical CSC (items as columns) built without a CSR intermediate.

    Column slices (blocks of items) are cheap on CSC, and ``.T`` shares the
    data buffers, so only this one copy of the matrix is ever in memory.
    """
    users = pairs["user_idx"].to_numpy().astype(np.int32)
    items = pairs["item_idx"].to_numpy().astype(np.int32)
    w = pairs["w"].to_numpy().astype(np.float32)
    del pairs
    gc.collect()
    n_users = int(users.max()) + 1
    # entries are sqrt(w) so that (A^T A)_ij yields the decayed co-purchase weight
    m = sp.coo_matrix((np.sqrt(w), (users, items)), shape=(n_users, n_items), dtype=np.float32).tocsc()
    m.sum_duplicates()
    log(f"user-item CSC built: {m.shape}, nnz={m.nnz:,}", t0)
    return m


def top_k_rows(block_scores: sp.csr_matrix, item_offset: int, item_ids: np.ndarray,
               t0: float, degrees: np.ndarray | None, min_raw: float) -> pl.DataFrame:
    """Extract top-K cosine neighbors per row from a sparse score block."""
    out_rows: list[np.ndarray] = []
    out_cols: list[np.ndarray] = []
    out_vals: list[np.ndarray] = []
    rows = block_scores.shape[0]
    for start in range(0, rows, 128):
        stop = min(start + 128, rows)
        raw = block_scores[start:stop].toarray().astype(np.float32)
        dense = raw.copy()
        if degrees is not None:
            d = np.sqrt(np.maximum(degrees[item_offset + start:item_offset + stop], 1e-12))[:, None]
            d2 = np.sqrt(np.maximum(degrees, 1e-12))[None, :]
            dense /= (d * d2)
        dense[raw < min_raw] = 0.0
        dense[dense < MIN_COSINE] = 0.0
        for r in range(stop - start):
            row = dense[r]
            k = min(TOP_K + 1, row.shape[0])
            idx = np.argpartition(-row, k - 1)[:k]
            idx = idx[row[idx] > 0]
            self_id = item_ids[item_offset + start + r]
            idx = idx[item_ids[idx] != self_id]  # drop self
            if idx.size == 0:
                continue
            order = idx[np.argsort(-row[idx])][:TOP_K]
            out_rows.append(np.full(order.size, item_offset + start + r, dtype=np.int32))
            out_cols.append(order.astype(np.int32))
            out_vals.append(row[order].astype(np.float32))
    if not out_rows:
        return pl.DataFrame(schema={"item_idx": pl.Int32, "neighbor_idx": pl.Int32, "score": pl.Float32})
    df = pl.DataFrame(
        {
            "item_idx": np.concatenate(out_rows),
            "neighbor_idx": np.concatenate(out_cols),
            "score": np.concatenate(out_vals),
        }
    )
    del out_rows, out_cols, out_vals
    return df


def neighbor_table(block_fn, n_items: int, item_ids: np.ndarray, t0: float,
                   degrees: np.ndarray | None = None, min_raw: float = 0.0,
                   cache_dir: Path | None = None) -> pl.DataFrame:
    """Blockwise similarity followed by top-K extraction (resumable).

    ``block_fn(start, stop)`` returns the (block_size x n_items) sparse score
    block for items [start, stop). Every finished block is written to
    ``cache_dir`` so an interrupted run resumes instead of recomputing.
    """
    id_map = dict(enumerate(item_ids.tolist()))
    tables: list[pl.DataFrame] = []
    for start in range(0, n_items, BLOCK):
        stop = min(start + BLOCK, n_items)
        part_file = cache_dir / f"block_{start:06d}.parquet"
        if part_file.exists():
            tables.append(pl.read_parquet(part_file).select("item_id", "neighbor_id", "score"))
            log(f"neighbor block {start:>6}/{n_items} (cached)", t0)
            continue
        scores = block_fn(start, stop).tocsr()
        df_block = top_k_rows(scores, start, item_ids, t0, degrees, min_raw)
        if df_block.height:
            df_block = df_block.with_columns(
                pl.col("item_idx").replace_strict(id_map, return_dtype=pl.Int64).alias("item_id"),
                pl.col("neighbor_idx").replace_strict(id_map, return_dtype=pl.Int64).alias("neighbor_id"),
            ).select("item_id", "neighbor_id", "score")
        else:
            df_block = pl.DataFrame(
                schema={"item_id": pl.Int64, "neighbor_id": pl.Int64, "score": pl.Float32}
            )
        df_block.write_parquet(part_file)
        tables.append(df_block)
        log(f"neighbor block {start:>6}/{n_items}", t0)
        del scores, df_block
    df = pl.concat(tables, how="vertical")
    del tables
    gc.collect()
    df = (
        df.with_columns(
            pl.col("score").rank("ordinal", descending=True).over("item_id").cast(pl.Int32).alias("sim_rank")
        )
        .sort("item_id", "sim_rank")
    )
    return df


def build_onehot(articles: pl.DataFrame) -> tuple[sp.csr_matrix, dict]:
    """One-hot encode the 9 categorical article features."""
    from scripts.pipeline.build_serving import FEATURE_COLS

    layout: dict[str, dict] = {}
    offset = 0
    cols: list[np.ndarray] = []
    for f in FEATURE_COLS:
        card = int(articles[f].max()) + 1
        layout[f] = {"offset": offset, "cardinality": card}
        cols.append(articles[f].fill_null(0).cast(pl.Int32).to_numpy() + offset)
        offset += card
    dim = offset
    n = articles.height
    k = len(FEATURE_COLS)
    indptr = np.arange(n + 1, dtype=np.int64) * k
    indices = np.stack(cols, axis=1).ravel().astype(np.int32)
    data = np.full(indices.shape[0], 1.0, dtype=np.float32)
    X = sp.csr_matrix((data, indices, indptr), shape=(n, dim))
    # row-normalize -> cosine similarity via dot product
    row_norm = np.sqrt(np.maximum(np.asarray(X.multiply(X).sum(axis=1)).ravel(), 1e-12))
    X = sp.diags(1.0 / row_norm) @ X
    return X.tocsr(), {"dim": dim, "features": layout}


def main() -> int:
    t0 = time.time()
    settings = get_settings()
    settings.ensure_dirs()
    print("=== Stage 2: item-neighbor models ===", flush=True)

    articles = pl.read_parquet(settings.serving_data_dir / "articles_serving.parquet").sort("article_id")
    item_ids = articles["article_id"].to_numpy().astype(np.int64)
    n_items = articles.height
    tx = tx_lazy(settings)

    pairs = build_weighted_pairs(settings, tx, articles, t0)
    matrix_csc = pairs_to_csc(pairs, n_items, t0)
    A_csr = matrix_csc.tocsr()  # same (users x items) matrix in CSR for fast products
    # d_i = sum_j w_ij  =  A^T (A @ 1_items)   because (A^T A)_ij = w_ij
    ones = np.ones(matrix_csc.shape[1], dtype=np.float32)  # n_items
    degrees = np.asarray(matrix_csc.T @ (matrix_csc @ ones)).ravel().astype(np.float64)
    degrees[degrees <= 0] = 1e-12
    gc.collect()

    log("computing collaborative neighbors (blockwise)…", t0)
    collab_cache = settings.models_dir / "tmp_neighbors_collab"
    collab_cache.mkdir(parents=True, exist_ok=True)
    collab = neighbor_table(
        lambda a, b: matrix_csc[:, a:b].T @ A_csr,
        n_items, item_ids, t0, degrees=degrees, min_raw=MIN_COWEIGHT,
        cache_dir=collab_cache,
    )
    del matrix_csc, A_csr, degrees
    gc.collect()
    collab.write_parquet(settings.models_dir / "item_neighbors_collab.parquet", statistics=True)
    log(f"item_neighbors_collab.parquet written ({collab.height:,})", t0)

    X, layout = build_onehot(articles)
    sp.save_npz(settings.models_dir / "article_onehot.npz", X)
    (settings.models_dir / "feature_layout.json").write_text(
        json.dumps({"half_life_days": HALF_LIFE_DAYS, "top_k": TOP_K, "item_order": "article_id asc", **layout}, indent=2)
    )
    log("computing content neighbors (blockwise)…", t0)
    XT = X.T.tocsr()
    content_cache = settings.models_dir / "tmp_neighbors_content"
    content_cache.mkdir(parents=True, exist_ok=True)
    content = neighbor_table(
        lambda a, b: X[a:b] @ XT,
        n_items, item_ids, t0, degrees=None, min_raw=0.0,
        cache_dir=content_cache,
    )
    content.write_parquet(settings.models_dir / "item_neighbors_content.parquet", statistics=True)
    log(f"item_neighbors_content.parquet written ({content.height:,})", t0)

    (settings.models_dir / "build_neighbors_meta.json").write_text(json.dumps({
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "half_life_days": HALF_LIFE_DAYS,
        "top_k": TOP_K,
        "min_cosine": MIN_COSINE,
        "min_coweight": MIN_COWEIGHT,
        "stage_timings": [{"stage": m, "seconds": round(d, 1)} for m, d in log_times],
    }, indent=2))
    # resume caches are only cleared once everything downstream succeeded
    shutil.rmtree(settings.models_dir / "tmp_pairs", ignore_errors=True)
    shutil.rmtree(settings.models_dir / "tmp_neighbors_collab", ignore_errors=True)
    shutil.rmtree(settings.models_dir / "tmp_neighbors_content", ignore_errors=True)
    log("stage 2 complete", t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
