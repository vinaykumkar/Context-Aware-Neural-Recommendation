"""Stage 3 — Generate hybrid candidate recommendations per customer.

For every customer with purchase history, a ranked pool of the top
``CANDIDATE_LIMIT`` articles is precomputed and stored with per-component
scores and reason codes. The web backend only reads these small bucket
files at request time — the 32M-row transaction source is never touched.

Hybrid score (all components normalized to 0..1 per customer):

    score = 0.45 * collaborative        (recency-decayed co-purchase neighbors)
          + 0.25 * content_similarity   (cosine between the customer's
                                         weighted article-feature profile
                                         and the candidate's features)
          + 0.20 * popularity           (blended total + 12-week demand)
          + 0.10 * repeat_purchase      (customer's own re-buy affinity)

Reason code = dominant weighted component.

Outputs: recommendations/buckets/bucket_XX.parquet (hash-bucketed by
customer id, same layout the backend queries).
"""
from __future__ import annotations

import gc
import json
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import polars as pl
import scipy.sparse as sp

from scripts._bootstrap import ROOT  # noqa: F401  (sys.path fix)
from backend.app.core.config import get_settings
from backend.app.core.serving import bucket_file
from scripts.pipeline.build_serving import bucket_expr, load_customer_buckets, tx_lazy, tx_slice_lazy

HALF_LIFE_DAYS = 90.0
CANDIDATE_LIMIT = 50
POP_CANDIDATES = 100
NEIGHBOR_LIMIT = 75           # top-N neighbor rows consulted per purchased item
CHUNK = 60_000                # purchases per explode-join chunk (bounds memory)
CONTENT_CHUNK = 50_000        # candidates per content-scoring chunk
WEIGHTS = {"collab": 0.45, "content": 0.25, "popularity": 0.20, "repurchase": 0.10}

log_times: list[tuple[str, float]] = []


def log(msg: str, t0: float) -> None:
    now = time.time()
    log_times.append((msg, now - t0))
    print(f"[{now - t0:8.1f}s] {msg}", flush=True)


def dominant_reason(
    collab_n: np.ndarray, content: np.ndarray, pop: np.ndarray, rep: np.ndarray
) -> np.ndarray:
    codes = np.array(["HYBRID", "COLLABORATIVE", "CONTENT_SIMILARITY", "POPULARITY", "REPEAT_PURCHASE"])
    contrib = np.stack(
        [WEIGHTS["collab"] * collab_n, WEIGHTS["content"] * content,
         WEIGHTS["popularity"] * pop, WEIGHTS["repurchase"] * rep]
    )
    # HYBRID when no single signal clearly dominates (winner < 1.25x runner-up)
    part = np.partition(contrib, -2, axis=0)
    top = contrib.max(axis=0)
    second = part[-2]
    hybrid = top < 1.25 * np.maximum(second, 1e-9)
    pick = np.where(hybrid, 0, np.argmax(contrib, axis=0) + 1)
    return codes[pick]


def load_models(settings) -> tuple[pl.DataFrame, pl.DataFrame, sp.csr_matrix, dict]:
    pop = pl.read_parquet(settings.models_dir / "article_popularity.parquet")
    nb = pl.read_parquet(settings.models_dir / "item_neighbors_collab.parquet")
    X = sp.load_npz(settings.models_dir / "article_onehot.npz").tocsr()
    layout = json.loads((settings.models_dir / "feature_layout.json").read_text())
    return pop, nb, X, layout


def decay_expr(max_date) -> pl.Expr:
    return 0.5 ** ((pl.lit(max_date) - pl.col("t_dat")).dt.total_days() / HALF_LIFE_DAYS)


def content_scores(S: np.ndarray, cand_user: np.ndarray, cand_item: np.ndarray,
                   X: sp.csr_matrix) -> np.ndarray:
    """cosine between customer profile direction and candidate one-hot row."""
    out = np.zeros(cand_user.shape[0], dtype=np.float32)
    S_norm = np.maximum(np.sqrt((S * S).sum(axis=1)), 1e-12).astype(np.float32)
    for start in range(0, cand_user.shape[0], CONTENT_CHUNK):
        stop = min(start + CONTENT_CHUNK, cand_user.shape[0])
        rows = X[cand_item[start:stop]].toarray().astype(np.float32)  # (chunk, dim)
        out[start:stop] = np.einsum("ij,ij->i", rows, S[cand_user[start:stop]])
    out /= S_norm[cand_user]
    return np.clip(out, 0.0, 1.0)


def process_bucket(k: int, settings, tx: pl.LazyFrame, art_map: pl.DataFrame,
                   user_map: pl.DataFrame, pop: pl.DataFrame, nb: pl.DataFrame,
                   X: sp.csr_matrix, max_date, t0: float) -> int:
    out_file = bucket_file(settings.recs_dir, k)
    if out_file.exists():
        df = pl.read_parquet(out_file)
        log(f"bucket {k:02d}: cached ({df.height:,} recs)", t0)
        return int(df["customer_id"].n_unique())
    ids = user_map.filter(pl.col("bucket") == k).select("customer_id", "user_idx")
    if ids.height == 0:
        return 0

    P = (
        tx_slice_lazy(tx, ids)
        .with_columns(decay_expr(max_date).alias("w"))
        .group_by("customer_id", "article_id")
        .agg(pl.col("w").sum())
        .join(art_map.lazy(), on="article_id", how="inner")
        .collect()
    )  # customer_id, article_id, w, item_idx
    if P.height == 0:
        return 0

    # local user index for this bucket
    local_ids = ids.with_row_index("u").with_columns(pl.col("u").cast(pl.Int32).alias("user_local"))
    P = P.join(local_ids.select("customer_id", "user_local"), on="customer_id", how="inner")
    user_stats = P.group_by("user_local").agg(
        pl.col("w").max().alias("max_w"), pl.col("w").sum().alias("W")
    )

    # ---- content profiles: S_u = sum_i w_i * X[i] -------------------------
    n_users_bucket = local_ids.height
    W_u = sp.coo_matrix(
        (P["w"].to_numpy().astype(np.float32),
         (P["user_local"].to_numpy().astype(np.int32), P["item_idx"].to_numpy().astype(np.int32))),
        shape=(n_users_bucket, X.shape[0]),
    ).tocsr()
    # (users x items) @ (items x dim) -> dense profile sums per customer
    S = (W_u @ X).toarray().astype(np.float32)
    del W_u
    gc.collect()

    # ---- candidate pool ---------------------------------------------------
    cand_frames: list[pl.DataFrame] = []
    nb_item = nb.select("item_id", "neighbor_id", "score")  # pre-filtered to NEIGHBOR_LIMIT in main()
    nb_item = nb_item.join(
        art_map.rename({"item_idx": "cand_idx"}), left_on="neighbor_id", right_on="article_id", how="inner"
    ).select("item_id", "cand_idx", "score")
    nb_item = nb_item.join(
        art_map.rename({"item_idx": "src_idx"}), left_on="item_id", right_on="article_id", how="inner"
    ).select("src_idx", "cand_idx", "score")

    purchases = P.select("user_local", "item_idx", "w")
    for start in range(0, purchases.height, CHUNK):
        chunk = purchases.slice(start, CHUNK)
        exploded = (
            chunk.join(nb_item, left_on="item_idx", right_on="src_idx", how="inner")
            .select("user_local", "cand_idx", (pl.col("w") * pl.col("score")).alias("collab_raw"))
        )
        agg = exploded.group_by("user_local", "cand_idx").agg(pl.col("collab_raw").sum())
        cand_frames.append(agg)
        del exploded
    collab_c = pl.concat(cand_frames) if cand_frames else None
    del cand_frames
    gc.collect()

    # repurchase candidates
    rep_c = (
        P.select("user_local", pl.col("item_idx").alias("cand_idx"), "w")
        .join(user_stats, on="user_local")
        .with_columns((pl.col("w") / pl.col("max_w").clip(1e-9)).alias("rep"))
        .select("user_local", "cand_idx", "rep")
    )
    # popularity candidates
    pop_c = (
        pop.sort("popularity_score", descending=True).head(POP_CANDIDATES)
        .select("article_id")
        .join(art_map.rename({"item_idx": "cand_idx"}), on="article_id", how="inner")
        .join(local_ids.select("user_local"), how="cross")
        .select("user_local", "cand_idx")
    )

    frames = [rep_c.select("user_local", "cand_idx"), pop_c]
    if collab_c is not None:
        frames.append(collab_c.select("user_local", "cand_idx"))
    union = pl.concat(frames, how="vertical").unique()
    log(f"bucket {k:02d}: union candidates={union.height:,}", t0)

    # ---- assemble component scores ---------------------------------------
    u = union.join(rep_c, on=["user_local", "cand_idx"], how="left").with_columns(pl.col("rep").fill_null(0.0))
    u = u.join(pop.select("article_id", "popularity_score").join(art_map.rename({"item_idx": "cand_idx"}), on="article_id", how="inner").select("cand_idx", "popularity_score"), on="cand_idx", how="left").with_columns(pl.col("popularity_score").fill_null(0.0))
    if collab_c is not None:
        u = u.join(collab_c, on=["user_local", "cand_idx"], how="left").with_columns(pl.col("collab_raw").fill_null(0.0))
    else:
        u = u.with_columns(pl.lit(0.0, dtype=pl.Float32).alias("collab_raw"))
    u = u.with_columns(pl.col("collab_raw").cast(pl.Float32), pl.col("popularity_score").cast(pl.Float32))

    cand_user = u["user_local"].to_numpy().astype(np.int64)
    cand_item = u["cand_idx"].to_numpy().astype(np.int64)
    content = content_scores(S, cand_user, cand_item, X)
    u = u.with_columns(pl.Series("content", content, dtype=pl.Float32))
    del S
    gc.collect()

    # per-user normalization of collab
    u = u.with_columns(pl.col("collab_raw").max().over("user_local").clip(1e-9).alias("collab_max"))
    u = u.with_columns((pl.col("collab_raw") / pl.col("collab_max")).alias("collab_n"))

    hybrid = (
        WEIGHTS["collab"] * pl.col("collab_n")
        + WEIGHTS["content"] * pl.col("content")
        + WEIGHTS["popularity"] * pl.col("popularity_score")
        + WEIGHTS["repurchase"] * pl.col("rep")
    )
    u = u.with_columns(hybrid.alias("score"))

    top = (
        u.sort("score", descending=True)
        .group_by("user_local")
        .head(CANDIDATE_LIMIT)
        .join(local_ids.select("user_local", "customer_id"), on="user_local", how="inner")
        .join(art_map.rename({"item_idx": "cand_idx"}).select("article_id", "cand_idx"), on="cand_idx", how="inner")
    )

    collab_n = top["collab_n"].to_numpy().astype(np.float32)
    content_v = top["content"].to_numpy().astype(np.float32)
    pop_v = top["popularity_score"].to_numpy().astype(np.float32)
    rep_v = top["rep"].to_numpy().astype(np.float32)
    top = top.with_columns(
        pl.Series("reason", dominant_reason(collab_n, content_v, pop_v, rep_v), dtype=pl.String)
    )

    out = (
        top.sort(["customer_id", "score"], descending=[False, True])
        .with_columns(pl.int_range(0, pl.len()).over("customer_id").alias("rank0"))
        .with_columns((pl.col("rank0") + 1).cast(pl.Int32).alias("rank"))
        .select(
            "customer_id",
            pl.col("article_id").cast(pl.Int64),
            "rank",
            pl.col("score").round(6).cast(pl.Float32),
            pl.col("collab_n").round(4).cast(pl.Float32).alias("comp_collaborative"),
            pl.col("content").round(4).cast(pl.Float32).alias("comp_content"),
            pl.col("popularity_score").round(4).cast(pl.Float32).alias("comp_popularity"),
            pl.col("rep").round(4).cast(pl.Float32).alias("comp_repurchase"),
            "reason",
        )
    )
    settings.recs_dir.mkdir(parents=True, exist_ok=True)
    out.write_parquet(bucket_file(settings.recs_dir, k), statistics=True)
    log(f"bucket {k:02d}: wrote {out.height:,} recs for {out['customer_id'].n_unique():,} customers", t0)
    return out.height


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    t0 = time.time()
    settings = get_settings()
    settings.ensure_dirs()
    print("=== Stage 3: recommendation generation ===", flush=True)

    pop, nb, X, layout = load_models(settings)
    nb = nb.filter(pl.col("sim_rank") <= NEIGHBOR_LIMIT).select("item_id", "neighbor_id", "score")
    gc.collect()
    articles = pl.read_parquet(settings.serving_data_dir / "articles_serving.parquet").sort("article_id")
    art_map = articles.select("article_id", pl.int_range(0, articles.height, dtype=pl.Int32).alias("item_idx"))
    del articles
    gc.collect()
    tx = tx_lazy(settings)
    max_date = tx.select(pl.col("t_dat").max()).collect().item()

    user_map = (
        pl.read_parquet(settings.serving_data_dir / "customers_serving.parquet")
        .select("customer_id", "has_purchases")
        .filter(pl.col("has_purchases"))
        .with_columns(bucket_expr().alias("bucket"))
        .with_row_index("u")
        .with_columns(pl.col("u").cast(pl.Int32).alias("user_idx"))
    )
    log(f"customers with purchases: {user_map.height:,}", t0)

    if argv:
        buckets = [int(b) for b in argv[0].split(",")]
    else:
        buckets = list(range(settings.num_buckets))

    total = 0
    for k in buckets:
        total += process_bucket(k, settings, tx, art_map, user_map, pop, nb, X, max_date, t0)
        gc.collect()

    if not argv:
        (settings.models_dir / "build_recs_meta.json").write_text(json.dumps({
            "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "half_life_days": HALF_LIFE_DAYS,
            "candidate_limit": CANDIDATE_LIMIT,
            "pop_candidates": POP_CANDIDATES,
            "neighbor_limit": NEIGHBOR_LIMIT,
            "weights": WEIGHTS,
            "customers_with_recs": total,
            "stage_timings": [{"stage": m, "seconds": round(d, 1)} for m, d in log_times],
        }, indent=2))
    log(f"stage 3 complete — {total:,} recommendation rows", t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
