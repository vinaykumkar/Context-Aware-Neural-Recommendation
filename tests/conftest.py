"""Test configuration: a tiny synthetic serving dataset, written to a temp
directory before any backend import, so get_settings() picks it up.

The fixture mirrors the real pipeline output schema exactly (same columns,
same bucket layout with NUM_BUCKETS=4).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---- configure environment BEFORE importing backend modules ----
_TMP = Path(tempfile.mkdtemp(prefix="hm_test_"))
os.environ["SERVING_DATA_DIR"] = str(_TMP / "serving")
os.environ["RECOMMENDATIONS_DIR"] = str(_TMP / "recs")
os.environ["MODELS_DIR"] = str(_TMP / "models")
os.environ["NUM_BUCKETS"] = "4"
os.environ["HISTORY_PER_CUSTOMER"] = "60"
os.environ["IMAGE_DIR"] = ""        # empty -> no provider (a real .env must not leak in)
os.environ.pop("IMAGE_URL_TEMPLATE", None)

SERVING = Path(os.environ["SERVING_DATA_DIR"])
MODELS = Path(os.environ["MODELS_DIR"])
RECS = Path(os.environ["RECOMMENDATIONS_DIR"])

FEATURES = {
    "product_type_name_index": [33, 39, 25],
    "product_group_name_index": [6, 3, 0],
    "graphical_appearance_name_index": [3, 14, 0],
    "colour_group_name_index": [2, 20, 0],
    "department_name_index": [5, 89, 166],
    "index_name_index": [7, 6, 2],
    "index_group_name_index": [0, 0, 3],
    "section_name_index": [22, 29, 34],
    "garment_group_name_index": [12, 1, 20],
}

ARTICLES = [663713001, 541518023, 505221004, 767541003, 902106001]
# first three articles use FEATURES rows (cycled), last two extra stats
CUST_ALICE = "a" * 56 + "00000001"
CUST_BOB = "b" * 56 + "00000002"
CUST_EMPTY = "c" * 56 + "00000003"   # profile exists, no purchases, no recs
CUST_GHOST = "d" * 56 + "00000004"   # not in customers_serving at all

# customer -> bucket via crc32 % 4
import zlib  # noqa: E402

BUCKET = {c: zlib.crc32(c.encode()) % 4 for c in (CUST_ALICE, CUST_BOB, CUST_EMPTY)}


def _customers() -> pl.DataFrame:
    rows = [
        dict(
            customer_id=CUST_ALICE, Active=1.0, club_member_status="ACTIVE",
            fashion_news_frequency="Regularly", age=29, purchase_count=4,
            unique_articles_count=3, average_price=0.02, total_spent=0.08,
            recency_days=30, purchase_frequency=0.02, customer_lifetime_days=700,
            first_purchase_date=date(2019, 1, 1), last_purchase_date=date(2020, 9, 1),
            top_product_group=6, top_product_type=33, top_colour_group=2,
            top_index_name=7, top_department=5, has_purchases=True,
        ),
        dict(
            customer_id=CUST_BOB, Active=0.0, club_member_status="PRE-CREATE",
            fashion_news_frequency="None", age=45, purchase_count=2,
            unique_articles_count=2, average_price=0.01, total_spent=0.02,
            recency_days=400, purchase_frequency=0.004, customer_lifetime_days=900,
            first_purchase_date=date(2018, 10, 1), last_purchase_date=date(2019, 10, 1),
            top_product_group=3, top_product_type=39, top_colour_group=20,
            top_index_name=6, top_department=89, has_purchases=True,
        ),
        dict(
            customer_id=CUST_EMPTY, Active=1.0, club_member_status="ACTIVE",
            fashion_news_frequency="None", age=33, purchase_count=0,
            unique_articles_count=0, average_price=None, total_spent=0.0,
            recency_days=None, purchase_frequency=0.0, customer_lifetime_days=None,
            first_purchase_date=None, last_purchase_date=None,
            top_product_group=None, top_product_type=None, top_colour_group=None,
            top_index_name=None, top_department=None, has_purchases=False,
        ),
    ]
    return pl.DataFrame(rows).with_columns(pl.col("age").cast(pl.Int32))


def _articles() -> pl.DataFrame:
    n = len(ARTICLES)
    return pl.DataFrame(
        {
            "article_id": ARTICLES,
            **{k: [v[i % 3] for i in range(n)] for k, v in FEATURES.items()},
            "purchase_count": [100, 80, 60, 40, 20],
            "unique_customers": [90, 70, 50, 35, 18],
            "avg_price": [0.02, 0.03, 0.015, 0.025, 0.01],
            "first_sale_date": [date(2018, 9, 20)] * n,
            "last_sale_date": [date(2020, 9, 20), date(2020, 8, 1), date(2020, 9, 10), date(2020, 5, 5), date(2020, 1, 1)],
            "sales_last_28d": [50, 40, 30, 0, 0],
            "sales_last_84d": [200, 150, 100, 10, 2],
        }
    )


def _popularity() -> pl.DataFrame:
    arts = _articles()
    return arts.select(
        "article_id", "purchase_count", "unique_customers", "sales_last_84d", "sales_last_28d", "last_sale_date"
    ).with_columns(
        (pl.col("sales_last_84d") / pl.col("sales_last_84d").max()).alias("popularity_score"),
    ).sort("popularity_score", descending=True).with_columns(
        pl.int_range(1, len(ARTICLES) + 1).alias("popularity_rank")
    )


def _history() -> dict[int, pl.DataFrame]:
    hist = pl.DataFrame(
        {
            "customer_id": [CUST_ALICE, CUST_ALICE, CUST_ALICE, CUST_ALICE, CUST_BOB, CUST_BOB],
            "article_id": [ARTICLES[0], ARTICLES[1], ARTICLES[2], ARTICLES[0], ARTICLES[1], ARTICLES[4]],
            "t_dat": [
                date(2020, 9, 1), date(2020, 8, 20), date(2020, 8, 20), date(2019, 1, 1),
                date(2019, 10, 1), date(2018, 10, 2),
            ],
            "price": [0.02, 0.03, 0.015, 0.02, 0.03, 0.01],
            "sales_channel_id": [2, 2, 1, 2, 1, 2],
        }
    )
    return {b: hist.filter(pl.col("customer_id").map_elements(lambda s: zlib.crc32(s.encode()) % 4 == b)) for b in range(4)}


def _recs() -> dict[int, pl.DataFrame]:
    rows = [
        # Alice: ARTICLES[0] is already purchased -> must be filtered by default
        dict(customer_id=CUST_ALICE, article_id=ARTICLES[3], rank=1, score=0.91,
             comp_collaborative=0.9, comp_content=0.5, comp_popularity=0.4, comp_repurchase=0.0,
             reason="COLLABORATIVE"),
        dict(customer_id=CUST_ALICE, article_id=ARTICLES[0], rank=2, score=0.85,
             comp_collaborative=0.8, comp_content=0.4, comp_popularity=0.9, comp_repurchase=0.3,
             reason="HYBRID"),
        dict(customer_id=CUST_ALICE, article_id=ARTICLES[1], rank=3, score=0.62,
             comp_collaborative=0.1, comp_content=0.6, comp_popularity=0.3, comp_repurchase=0.2,
             reason="CONTENT_SIMILARITY"),
        dict(customer_id=CUST_BOB, article_id=ARTICLES[2], rank=1, score=0.5,
             comp_collaborative=0.2, comp_content=0.2, comp_popularity=0.8, comp_repurchase=0.0,
             reason="POPULARITY"),
    ]
    df = pl.DataFrame(rows)
    return {b: df.filter(pl.col("customer_id").map_elements(lambda s: zlib.crc32(s.encode()) % 4 == b)) for b in range(4)}


def _meta() -> dict:
    return {
        "built_at": "2026-08-30 00:00:00",
        "pipeline_version": "1.0.0",
        "dataset": {
            "n_transactions": 31788324,
            "min_date": "2018-09-20",
            "max_date": "2020-09-22",
            "n_active_customers": 1362281,
            "n_purchased_articles": 104547,
            "n_articles": len(ARTICLES),
            "total_seconds": 100.0,
        },
        "serving": {"num_buckets": 4, "history_per_customer": 60},
        "stage_timings": [],
    }


def build_fixture() -> None:
    (SERVING / "history").mkdir(parents=True, exist_ok=True)
    (RECS / "buckets").mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)

    _customers().write_parquet(SERVING / "customers_serving.parquet")
    _articles().write_parquet(SERVING / "articles_serving.parquet")
    _popularity().write_parquet(MODELS / "article_popularity.parquet")
    for b, df in _history().items():
        df.write_parquet(SERVING / "history" / f"bucket_{b:02d}.parquet")
    for b, df in _recs().items():
        df.write_parquet(RECS / "buckets" / f"bucket_{b:02d}.parquet")
    pl.DataFrame({
        "article_id": ARTICLES,
        "product_type_name": ["Sweater", "Trousers", "Dress", "Socks", "Leggings"],
        "product_group_name": ["Garment Upper body", "Garment Lower body", "Dress", "Socks and Tights", "Garment Lower body"],
        "graphical_appearance_name": ["Solid", "Denim", "Solid", "Solid", "Solid"],
        "colour_group_name": ["Black", "Blue", "Red", "White", "Black"],
        "department_name": ["Jersey", "Denim", "Woven", "Basics", "Jersey"],
        "index_name": ["Ladieswear", "Divided", "Ladieswear", "Baby", "Ladieswear"],
        "index_group_name": ["Ladieswear", "Divided", "Ladieswear", "Baby", "Ladieswear"],
        "section_name": ["Womens Knitwear", "Mama", "Womens Everyday", "Baby Essentials", "Womens Leggings"],
        "garment_group_name": ["Jersey Basic", "Trousers Denim", "Dress", "Under-, Nightwear", "Jersey Basic"],
    }).write_parquet(SERVING / "articles_display.parquet")
    (SERVING / "meta.json").write_text(json.dumps(_meta()))
    (MODELS / "build_recs_meta.json").write_text(json.dumps({
        "built_at": "2026-08-30 00:00:00",
        "half_life_days": 90,
        "candidate_limit": 50,
        "pop_candidates": 200,
        "neighbor_limit": 100,
        "weights": {"collab": 0.45, "content": 0.25, "popularity": 0.20, "repurchase": 0.10},
        "customers_with_recs": 2,
        "stage_timings": [],
    }))


build_fixture()
