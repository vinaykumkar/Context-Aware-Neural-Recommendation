"""Stage 3 — Generate hybrid candidate recommendations per customer.

Disk-backed DuckDB implementation designed for 8 GB machines:
  * every per-bucket computation runs as SQL with ``memory_limit=2GB`` and a
    temp spill directory — hash joins/aggregations spill to disk instead of
    aborting;
  * customers are processed in independent buckets (crc32 % 32) with
    checkpoint/resume: finished buckets are skipped on rerun;
  * the 32M-row transaction table is only ever scanned through DuckDB's
    streaming operators, one bucket predicate at a time.

Hybrid score (components normalized 0..1 per customer):

    score = 0.45 * collaborative        (recency-decayed co-purchase neighbors)
          + 0.25 * content_similarity   (cosine between the customer's weighted
                                         article-attribute profile direction and
                                         the candidate's unit-norm one-hot vector)
          + 0.20 * popularity           (blended total + 12-week demand)
          + 0.10 * repeat_purchase      (customer's own re-buy affinity)

Reason code = dominant weighted component (HYBRID on near-ties).

Output: recommendations/buckets/bucket_XX.parquet —
customer_id, article_id, rank, score, comp_collaborative, comp_content,
comp_popularity, comp_repurchase, reason.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import polars as pl
import scipy.sparse as sp

from scripts._bootstrap import ROOT  # noqa: F401  (sys.path fix)
from backend.app.core.config import get_settings
from backend.app.core.serving import bucket_file
from scripts.pipeline.build_serving import bucket_expr, load_customer_buckets

NEIGHBOR_LIMIT = 40
SEED_ITEMS = 8                # per-customer seeds for the neighbor explosion
EXPLODE_NB = 15               # neighbor rank cap used when generating candidates
PRELIM_KEEP = 100             # candidates that receive exact content scoring
POP_CANDIDATES = 60
CANDIDATE_LIMIT = 50
WEIGHTS = {"collab": 0.45, "content": 0.25, "popularity": 0.20, "repurchase": 0.10}
DUCKDB_MEMORY_LIMIT = "2000MB"
DUCKDB_THREADS = 4

log_times: list[tuple[str, float]] = []


def log(msg: str, t0: float) -> None:
    now = time.time()
    log_times.append((msg, now - t0))
    print(f"[{now - t0:8.1f}s] {msg}", flush=True)


def ensure_support_tables(settings) -> None:
    """One-time helper tables used by the SQL per bucket."""
    t0 = time.time()
    buckets_file = settings.models_dir / "customer_buckets.parquet"
    if not buckets_file.exists():
        tbl = (
            pl.read_parquet(settings.serving_data_dir / "customers_serving.parquet")
            .select("customer_id", "has_purchases")
            .filter(pl.col("has_purchases"))
            .with_columns(bucket_expr().alias("bucket"))
        )
        tbl.write_parquet(buckets_file)
        log(f"customer_buckets.parquet written ({tbl.height:,})", t0)

    levels_file = settings.models_dir / "article_levels.parquet"
    if not levels_file.exists():
        articles = pl.read_parquet(settings.serving_data_dir / "articles_serving.parquet").sort("article_id")
        X: sp.csr_matrix = sp.load_npz(settings.models_dir / "article_onehot.npz")
        Xc = X.tocoo()
        levels = pl.DataFrame({
            "row": Xc.row.astype(np.int64),
            "level": Xc.col.astype(np.int64),
        }).join(
            articles.select(
                "article_id",
                pl.int_range(0, articles.height, dtype=pl.Int64).alias("row"),
            ),
            on="row",
            how="inner",
        ).select("article_id", "level")
        levels.write_parquet(levels_file)
        log(f"article_levels.parquet written ({levels.height:,})", time.time())

    # slim, sorted neighbor table: smaller hash-join build side per bucket
    nb75_file = settings.models_dir / "tmp_nb_top.parquet"
    if not nb75_file.exists():
        (
            pl.scan_parquet(settings.models_dir / "item_neighbors_collab.parquet")
            .filter(pl.col("sim_rank") <= NEIGHBOR_LIMIT)
            .select("item_id", "neighbor_id", "score", "sim_rank")
            .sort("item_id")
            .collect(engine="streaming")
            .write_parquet(nb75_file)
        )
        log("tmp_nb_top.parquet written", time.time())


def _connect(settings) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{DUCKDB_MEMORY_LIMIT}'")
    con.execute(f"SET threads={DUCKDB_THREADS}")
    con.execute(f"SET temp_directory='{(settings.models_dir / 'tmp_duckdb').as_posix()}'")
    con.execute(f"SET preserve_insertion_order=false")
    return con


def build_bucket(k: int, settings, max_date: str) -> int:
    out_file = bucket_file(settings.recs_dir, k)
    if out_file.exists():
        n = pl.scan_parquet(out_file).select(pl.len()).collect().item()
        log(f"bucket {k:02d}: cached ({n:,} rows)", time.time())
        return n

    t0 = time.time()
    con = _connect(settings)
    q = lambda s: s.as_posix() if isinstance(s, Path) else s  # noqa: E731

    tx_glob = q(Path(settings.data_dir / "transactions").as_posix()) + "/part-*.parquet"
    buckets_tbl = q(settings.models_dir / "customer_buckets.parquet")
    nb_tbl = q(settings.models_dir / "item_neighbors_collab.parquet")
    pop_tbl = q(settings.models_dir / "article_popularity.parquet")
    levels_tbl = q(settings.models_dir / "article_levels.parquet")

    con.execute(f"""
        CREATE TEMP TABLE p0 AS
        SELECT t.customer_id,
               t.article_id,
               SUM(POWER(0.5, DATEDIFF('day', t.t_dat, DATE '{max_date}') / 90.0)) AS w
        FROM read_parquet('{tx_glob}') t
        WHERE t.customer_id IN (SELECT customer_id FROM read_parquet('{buckets_tbl}') WHERE bucket = {k})
        GROUP BY 1, 2
    """)
    con.execute("""
        CREATE TEMP TABLE p AS
        SELECT customer_id, article_id, w,
               MAX(w) OVER (PARTITION BY customer_id) AS w_max
        FROM p0
    """)
    n_p = con.execute("SELECT COUNT(*), COUNT(DISTINCT customer_id) FROM p").fetchone()
    log(f"bucket {k:02d}: {n_p[0]:,} purchased pairs / {n_p[1]:,} customers", t0)

    # Seed items: the customer's top-8 weighted (recency-decayed) articles.
    # Neighbor explosion over ALL purchases would create ~30M candidate rows
    # per bucket — infeasible on 8 GB machines; favorite items carry nearly
    # all of the collaborative signal.
    con.execute(f"""
        CREATE TEMP TABLE seed AS
        SELECT customer_id, article_id, w
        FROM (
            SELECT customer_id, article_id, w,
                   ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY w DESC) AS rn
            FROM p0
        ) t
        WHERE rn <= {SEED_ITEMS}
    """)
    con.execute(f"""
        CREATE TEMP TABLE cand AS
        SELECT s.customer_id,
               n.neighbor_id AS article_id,
               SUM(s.w * n.score) AS collab_raw
        FROM seed s
        JOIN read_parquet('{q(settings.models_dir / "tmp_nb_top.parquet")}') n
          ON n.item_id = s.article_id AND n.sim_rank <= {EXPLODE_NB}
        GROUP BY 1, 2
    """)
    log(f"bucket {k:02d}: collab candidates {con.execute('SELECT COUNT(*) FROM cand').fetchone()[0]:,}", t0)

    con.execute(f"""
        CREATE TEMP TABLE pop AS
        SELECT article_id, popularity_score FROM read_parquet('{pop_tbl}')
        ORDER BY popularity_score DESC LIMIT {POP_CANDIDATES}
    """)
    # single-pass aggregation: sources stream straight into the group-by,
    # nothing is materialized twice
    con.execute("""
        CREATE TEMP TABLE u AS
        WITH src AS (
            SELECT customer_id, article_id, collab_raw, 0.0 AS rep, 0.0 AS pop_score FROM cand
            UNION ALL
            SELECT customer_id, article_id, 0.0 AS collab_raw,
                   w / GREATEST(w_max, 1e-9) AS rep, 0.0 AS pop_score FROM p
            UNION ALL
            SELECT b.customer_id, pop.article_id, 0.0, 0.0, pop.popularity_score
            FROM (SELECT DISTINCT customer_id FROM p) b CROSS JOIN pop
        )
        SELECT customer_id, article_id,
               SUM(collab_raw) AS collab_raw,
               MAX(rep) AS rep,
               MAX(pop_score) AS pop_score
        FROM src
        GROUP BY 1, 2
    """)
    del_union = con.execute("SELECT COUNT(*) FROM u").fetchone()[0]
    log(f"bucket {k:02d}: union candidates {del_union:,}", t0)

    # content similarity: cosine between the customer's weighted profile
    # direction and the candidate's unit-norm one-hot vector.
    #   numerator   = sum over candidate levels of S_l  (S_l = sum of w)
    #   denominator = sqrt(sum over ALL levels of S_l^2)   (the w-sum cancels)
    con.execute(f"""
        CREATE TEMP TABLE s AS
        SELECT p.customer_id, x.level, SUM(p.w) AS s
        FROM p JOIN read_parquet('{levels_tbl}') x ON x.article_id = p.article_id
        GROUP BY 1, 2
    """)
    con.execute("""
        CREATE TEMP TABLE snorm AS
        SELECT customer_id, SQRT(SUM(s * s)) AS snorm FROM s GROUP BY 1
    """)

    # Phase 1: preliminary ranking on collaborative + popularity + repeat
    # signals; keep the top PRELIM_KEEP per customer.
    wc, wct, wp, wr = (WEIGHTS[x] for x in ("collab", "content", "popularity", "repurchase"))
    con.execute(f"""
        CREATE TEMP TABLE prelim AS
        SELECT customer_id, article_id, collab_n, pop_score, rep,
               {wc} * collab_n + {wp} * pop_score + {wr} * rep AS s0
        FROM (
            SELECT customer_id, article_id, pop_score, rep,
                   collab_raw / GREATEST(MAX(collab_raw) OVER (PARTITION BY customer_id), 1e-12) AS collab_n
            FROM u
        )
        QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY s0 DESC) <= {PRELIM_KEEP}
    """)
    log(f"bucket {k:02d}: preliminary candidates {con.execute('SELECT COUNT(*) FROM prelim').fetchone()[0]:,}", t0)

    # Phase 2: exact content scores for the preliminary set only (a documented
    # approximation — content can reorder the preliminary top-{PRELIM_KEEP}
    # but is not evaluated for the long tail), then final hybrid ranking.
    con.execute(f"""
        CREATE TEMP TABLE clev AS
        SELECT pr.customer_id, pr.article_id, SUM(s.s) AS ssum
        FROM prelim pr
        JOIN read_parquet('{levels_tbl}') x ON x.article_id = pr.article_id
        JOIN s ON s.customer_id = pr.customer_id AND s.level = x.level
        GROUP BY 1, 2
    """)

    wc, wct, wp, wr = (WEIGHTS[x] for x in ("collab", "content", "popularity", "repurchase"))
    con.execute(f"""
        CREATE TEMP TABLE scored AS
        SELECT pr.customer_id,
               pr.article_id,
               COALESCE(c.ssum, 0.0) / GREATEST(sn.snorm * 3.0, 1e-12) AS content,  -- |x_c| = sqrt(9 features)
               pr.collab_n,
               pr.pop_score,
               pr.rep,
               {wc} * pr.collab_n
             + {wct} * (COALESCE(c.ssum, 0.0) / GREATEST(sn.snorm * 3.0, 1e-12))
             + {wp} * pr.pop_score
             + {wr} * pr.rep AS hybrid
        FROM prelim pr
        LEFT JOIN clev c ON c.customer_id = pr.customer_id AND c.article_id = pr.article_id
        LEFT JOIN snorm sn ON sn.customer_id = pr.customer_id
    """)
    con.execute(f"""
        CREATE TEMP TABLE ranked AS
        SELECT customer_id, article_id, content, collab_n, pop_score, rep, hybrid
        FROM scored
        QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY hybrid DESC) <= {CANDIDATE_LIMIT}
    """)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"""
        COPY (
            WITH c AS (
                SELECT *, {wc} * collab_n AS c_collab, {wct} * content AS c_content,
                       {wp} * pop_score AS c_pop, {wr} * rep AS c_rep
                FROM ranked
            )
            SELECT customer_id,
                   CAST(article_id AS BIGINT) AS article_id,
                   CAST(ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY hybrid DESC) AS INTEGER) AS rank,
                   CAST(ROUND(hybrid, 6) AS FLOAT) AS score,
                   CAST(ROUND(collab_n, 4) AS FLOAT) AS comp_collaborative,
                   CAST(ROUND(content, 4) AS FLOAT) AS comp_content,
                   CAST(ROUND(pop_score, 4) AS FLOAT) AS comp_popularity,
                   CAST(ROUND(rep, 4) AS FLOAT) AS comp_repurchase,
                   CASE
                       WHEN GREATEST(c_collab, c_content, c_pop, c_rep) < 1.25 * LEAST(
                            GREATEST(c_collab, c_content, c_pop),
                            GREATEST(c_collab, c_content, c_rep),
                            GREATEST(c_collab, c_pop, c_rep),
                            GREATEST(c_content, c_pop, c_rep))
                       THEN 'HYBRID'
                       WHEN c_collab >= GREATEST(c_content, c_pop, c_rep) THEN 'COLLABORATIVE'
                       WHEN c_content >= GREATEST(c_collab, c_pop, c_rep) THEN 'CONTENT_SIMILARITY'
                       WHEN c_pop >= GREATEST(c_collab, c_content, c_rep) THEN 'POPULARITY'
                       ELSE 'REPEAT_PURCHASE'
                   END AS reason
            FROM c
            ORDER BY customer_id, rank
        ) TO '{q(out_file)}' (FORMAT PARQUET)
    """)
    n_out = con.execute(f"SELECT COUNT(*), COUNT(DISTINCT customer_id) FROM read_parquet('{q(out_file)}')").fetchone()
    con.close()
    log(f"bucket {k:02d}: wrote {n_out[0]:,} recs for {n_out[1]:,} customers", t0)
    return n_out[1]


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    t0 = time.time()
    settings = get_settings()
    settings.ensure_dirs()
    (settings.models_dir / "tmp_duckdb").mkdir(parents=True, exist_ok=True)
    print("=== Stage 3: recommendation generation (DuckDB, disk-backed) ===", flush=True)

    ensure_support_tables(settings)

    meta_file = settings.serving_data_dir / "meta.json"
    max_date = json.loads(meta_file.read_text())["dataset"]["max_date"] if meta_file.exists() else "2020-09-22"

    if argv:
        buckets = [int(b) for b in argv[0].split(",")]
        all_buckets = False
    else:
        buckets = list(range(settings.num_buckets))
        all_buckets = True

    total = 0
    for k in buckets:
        total += build_bucket(k, settings, max_date)

    meta_out = settings.models_dir / "build_recs_meta.json"
    if all_buckets:
        meta_out.write_text(json.dumps({
            "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "half_life_days": 90.0,
            "candidate_limit": CANDIDATE_LIMIT,
            "pop_candidates": POP_CANDIDATES,
            "neighbor_limit": NEIGHBOR_LIMIT,
            "weights": WEIGHTS,
            "customers_with_recs": total,
            "engine": "duckdb",
            "stage_timings": [{"stage": m, "seconds": round(d, 1)} for m, d in log_times],
        }, indent=2))
    import shutil

    shutil.rmtree(settings.models_dir / "tmp_duckdb", ignore_errors=True)
    log(f"stage 3 complete — {total:,} customers with recommendations", t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
