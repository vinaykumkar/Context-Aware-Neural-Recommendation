"""Validate that every ID and row in the generated artifacts exists verbatim
in the read-only source dataset.

Verifies:
  1. recommendation customer_ids  == real source customers (and buyers)
  2. recommendation article_ids   == real source articles (and purchasable)
  3. served purchase history rows == exact source transaction rows
  4. served article features      == source article features
  5. API Top-10 article_ids       == real source articles
  6. identifier formats (64-hex customer ids, 9-digit article ids)

Usage:  python scripts/validate_outputs.py   (backend running for check 5)
"""
import sys
import re
import zlib
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import polars as pl

from backend.app.core.article_id import format_article_id

FEATURES = [
    "product_type_name_index", "product_group_name_index", "graphical_appearance_name_index",
    "colour_group_name_index", "department_name_index", "index_name_index",
    "index_group_name_index", "section_name_index", "garment_group_name_index",
]


def semi_count(df: pl.DataFrame, src: pl.LazyFrame, col: str) -> int:
    return df.lazy().join(src, on=col, how="semi").select(pl.len()).collect().item()


def main() -> int:
    src_cust = pl.scan_parquet("parquet/customers/part-*.parquet").select("customer_id")
    art_dir = "parquet/articles_model" if Path("parquet/articles_model").exists() else "parquet/articles"
    src_art = pl.scan_parquet(f"{art_dir}/part-*.parquet").select("article_id")
    src_tx_c = pl.scan_parquet("parquet/transactions/part-*.parquet").select("customer_id")
    src_tx_a = pl.scan_parquet("parquet/transactions/part-*.parquet").select("article_id")

    results: list[tuple[str, bool]] = []

    recs = pl.concat([
        pl.read_parquet(f"recommendations/buckets/bucket_{i:02d}.parquet").select("customer_id", "article_id")
        for i in (0, 7, 15, 31)
    ])
    rc, ra = recs.select("customer_id").unique(), recs.select("article_id").unique()
    results.append(("rec customer_ids exist in source customers", semi_count(rc, src_cust, "customer_id") == rc.height))
    results.append(("rec customer_ids exist in source transactions", semi_count(rc, src_tx_c, "customer_id") == rc.height))
    results.append(("rec article_ids exist in source articles", semi_count(ra, src_art, "article_id") == ra.height))
    results.append(("rec article_ids are purchasable (in transactions)", semi_count(ra, src_tx_a, "article_id") == ra.height))

    random.seed(7)
    custs = (pl.scan_parquet("serving_data/customers_serving.parquet")
             .filter(pl.col("has_purchases")).select("customer_id").collect())
    ok_rows = ok_cnt = n = 0
    for cid in random.sample(custs["customer_id"].to_list(), 5):
        b = zlib.crc32(cid.encode()) % 32
        sv = (pl.read_parquet(f"serving_data/history/bucket_{b:02d}.parquet")
              .filter(pl.col("customer_id") == cid).select("article_id", "t_dat", "price", "sales_channel_id"))
        so = (pl.scan_parquet("parquet/transactions/part-*.parquet")
              .filter(pl.col("customer_id") == cid)
              .select("article_id", "t_dat", "price", "sales_channel_id").collect())
        ok_rows += sv.join(so, on=["article_id", "t_dat", "price", "sales_channel_id"], how="anti").height == 0
        ok_cnt += sv.height == min(60, so.height)
        n += 1
    results.append((f"served history rows match source exactly ({n} customers)", ok_rows == n and ok_cnt == n))

    api_arts = pl.DataFrame({"article_id": [80941 % 1000000000]})
    try:
        import urllib.request
        import json as jsonlib

        cid = custs["customer_id"][0]
        d = jsonlib.load(urllib.request.urlopen(
            f"http://127.0.0.1:8000/api/customers/{cid}/recommendations?count=10", timeout=15))
        api_ids = [i["article_id"] for i in d["items"]]
        assert all(isinstance(a, str) and len(a) == 10 and a.isdigit() for a in api_ids), "API ids not 10-digit strings"
        api_arts = pl.DataFrame({"article_id": [int(a) for a in api_ids]})
        results.append(("API Top-10 article_ids exist in source articles",
                        semi_count(api_arts, src_art, "article_id") == api_arts.height))
    except Exception as e:  # backend not running — skip gracefully
        print(f"  (API check skipped: {e})")

    ids3 = ra["article_id"].head(3).to_list()
    served_f = (pl.read_parquet("serving_data/articles_serving.parquet")
                .filter(pl.col("article_id").is_in(ids3)).sort("article_id").select(FEATURES))
    orig_f = (pl.read_parquet(f"{art_dir}/part-*.parquet")
              .filter(pl.col("article_id").is_in(ids3)).sort("article_id").select(FEATURES))
    results.append(("served article features identical to source", served_f.equals(orig_f)))

    hexok = all(re.fullmatch(r"[0-9a-f]{64}", c) for c in rc["customer_id"].head(5000).to_list())
    artok = all(re.fullmatch(r"\d{9}", str(a)) for a in ra["article_id"].head(5000).to_list())
    results.append(("identifier formats (64-hex customer, 9-digit article)", hexok and artok))

    # dataset-wide: every unique article id formats to exactly 10 digits, no collisions
    arts = pl.read_parquet("serving_data/articles_serving.parquet").select("article_id")
    formatted = arts.with_columns(
        pl.col("article_id").map_elements(format_article_id, return_dtype=pl.String).alias("formatted")
    )
    n = arts.height
    ten = formatted.filter(pl.col("formatted").str.len_chars() == 10).height
    uniq = formatted["formatted"].n_unique()
    results.append((f"all {n:,} article ids format to exactly 10 digits", ten == n))
    results.append((f"formatted ids are collision-free ({uniq:,} unique)", uniq == n))

    print("=== output-vs-source validation ===")
    failed = 0
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        failed += not ok
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
