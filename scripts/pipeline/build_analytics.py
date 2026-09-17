"""Stage 4 — Sales analytics artifacts (AOV + article age affinity).

Computed with disk-backed DuckDB (memory_limit, temp spill) — never pandas
over the full 31.8M-row transaction table.

Outputs
-------
serving_data/monthly_aov.parquet
    month (YYYY-MM), total_revenue, total_orders, average_order_value

    ORDER DEFINITION (honest): the H&M transaction data has NO order id and
    each row is a single item purchase. An "order" is therefore aggregated as
    one customer's purchases on one date through one sales channel — a
    shopping trip (customer_id, t_dat, sales_channel_id). This is the most
    defensible order-level aggregation available; no order id is fabricated.
    Revenue uses the dataset's normalized price units (no currency invented).

serving_data/article_age_affinity.parquet
    article_id, age_band, purchase_count — real purchase counts per article
    from customers in each age band (used for age-aware reranking of the
    precomputed recommendation pool; bands derive from the actual 16–99
    age distribution).

Usage:  python scripts/build_analytics.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import duckdb

from backend.app.core.config import get_settings

AGE_BANDS = [
    ("under_18", 0, 17),
    ("18_24", 18, 24),
    ("25_34", 25, 34),
    ("35_44", 35, 44),
    ("45_54", 45, 54),
    ("55_plus", 55, 200),
]


def connect(settings) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("SET memory_limit='1600MB'")
    con.execute("SET threads=4")
    con.execute("SET temp_directory='{}'".format((settings.models_dir / "tmp_analytics").as_posix()))
    con.execute("SET preserve_insertion_order=false")
    return con


def build_monthly_aov(con, settings, t0) -> None:
    tx = (settings.data_dir / "transactions").as_posix() + "/part-*.parquet"
    out = settings.serving_data_dir / "monthly_aov.parquet"
    con.execute(f"""
        COPY (
            WITH trips AS (
                SELECT customer_id, t_dat, sales_channel_id, SUM(price) AS trip_value
                FROM read_parquet('{tx}')
                GROUP BY 1, 2, 3
            )
            SELECT strftime(t_dat, '%Y-%m') AS month,
                   CAST(ROUND(SUM(trip_value), 4) AS DOUBLE)  AS total_revenue,
                   CAST(COUNT(*) AS BIGINT)                   AS total_orders,
                   CAST(ROUND(SUM(trip_value) / COUNT(*), 6) AS DOUBLE) AS average_order_value
            FROM trips
            GROUP BY 1
            ORDER BY 1
        ) TO '{out.as_posix()}' (FORMAT PARQUET)
    """)
    n = con.execute(f"SELECT COUNT(*), MIN(month), MAX(month) FROM read_parquet('{out.as_posix()}')").fetchone()
    print(f"[{time.time() - t0:7.1f}s] monthly_aov.parquet: {n[0]} months ({n[1]} → {n[2]})", flush=True)


def build_age_affinity(con, settings, t0) -> None:
    tx = (settings.data_dir / "transactions").as_posix() + "/part-*.parquet"
    cust = (settings.serving_data_dir / "customers_serving.parquet").as_posix()
    out = settings.serving_data_dir / "article_age_affinity.parquet"
    bands_sql = "CASE " + " ".join(
        f"WHEN age BETWEEN {lo} AND {hi} THEN '{name}'" for name, lo, hi in AGE_BANDS
    ) + " END"
    con.execute(f"""
        COPY (
            SELECT t.article_id,
                   {bands_sql} AS age_band,
                   CAST(COUNT(*) AS BIGINT) AS purchase_count
            FROM read_parquet('{tx}') t
            JOIN read_parquet('{cust}') c USING (customer_id)
            GROUP BY 1, 2
        ) TO '{out.as_posix()}' (FORMAT PARQUET)
    """)
    n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{out.as_posix()}')").fetchone()
    print(f"[{time.time() - t0:7.1f}s] article_age_affinity.parquet: {n[0]:,} rows", flush=True)


def main() -> int:
    t0 = time.time()
    settings = get_settings()
    settings.ensure_dirs()
    (settings.models_dir / "tmp_analytics").mkdir(parents=True, exist_ok=True)
    print("=== Stage 4: sales analytics (DuckDB, disk-backed) ===", flush=True)
    con = connect(settings)
    try:
        build_monthly_aov(con, settings, t0)
        build_age_affinity(con, settings, t0)
    finally:
        con.close()
    import shutil

    shutil.rmtree(settings.models_dir / "tmp_analytics", ignore_errors=True)
    print(f"[{time.time() - t0:7.1f}s] stage 4 complete", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
