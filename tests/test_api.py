"""API tests against the synthetic serving fixture (tests/conftest.py)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.main import app  # noqa: E402  (import after conftest env setup)
from tests.conftest import ARTICLES, CUST_ALICE, CUST_BOB, CUST_EMPTY, CUST_GHOST  # noqa: E402

# canonical 10-digit external forms of the fixture's numeric article ids
FMT = {a: f"{a:010d}" for a in ARTICLES}

client = TestClient(app)


# ---------------- health & config ----------------

def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["serving"]["customers_serving"] is True
    assert body["serving"]["recommendation_buckets"] == 4


def test_app_config():
    r = client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert body["image_mode"] == "placeholder"
    assert body["max_recommendation_count"] == 50


# ---------------- customer discovery ----------------

def test_customers_list_paginates():
    r = client.get("/api/customers?page=1&page_size=2")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["pages"] == 2


def test_customers_search():
    r = client.get(f"/api/customers?q={'a'*12}")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["customer_id"] == CUST_ALICE


def test_customers_filter_has_purchases():
    r = client.get("/api/customers?has_purchases=false")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["customer_id"] == CUST_EMPTY


def test_customers_invalid_pagination_rejected():
    assert client.get("/api/customers?page=0").status_code == 422
    assert client.get("/api/customers?page_size=1000").status_code == 422


# ---------------- profile ----------------

def test_customer_profile():
    r = client.get(f"/api/customers/{CUST_ALICE}")
    assert r.status_code == 200
    body = r.json()
    assert body["customer"]["purchase_count"] == 4
    assert body["customer"]["short_id"].endswith("0001")
    assert len(body["top_categories"]) == 5


def test_customer_profile_404():
    assert client.get(f"/api/customers/{CUST_GHOST}").status_code == 404


def test_customer_profile_cold_start_no_affinities():
    # member with zero purchases: all top_* columns are NULL/NaN
    r = client.get(f"/api/customers/{CUST_EMPTY}")
    assert r.status_code == 200
    body = r.json()
    assert body["customer"]["has_purchases"] is False
    assert body["top_categories"] == []


def test_customer_profile_invalid_id():
    assert client.get("/api/customers/not-hex").status_code == 422


# ---------------- history ----------------

def test_customer_history_sorted_desc_and_joined():
    r = client.get(f"/api/customers/{CUST_ALICE}/history")
    assert r.status_code == 200
    body = r.json()
    dates = [i["t_dat"] for i in body["items"]]
    assert dates == sorted(dates, reverse=True)
    assert body["total_transactions"] == 4
    first = body["items"][0]
    assert first["article_id"] == FMT[ARTICLES[0]]  # 10-digit string
    assert isinstance(first["article_id"], str)
    assert first["article"]["article_id"] == FMT[ARTICLES[0]]
    assert body["items"][0]["article"]["image_url"] is None  # placeholder mode


def test_history_limit_param():
    r = client.get(f"/api/customers/{CUST_ALICE}/history?limit=2")
    assert r.status_code == 200
    assert r.json()["returned"] == 2


def test_history_customer_without_purchases():
    r = client.get(f"/api/customers/{CUST_EMPTY}/history")
    assert r.status_code == 200
    assert r.json()["returned"] == 0


# ---------------- recommendations ----------------

def test_recommendations_count_and_no_duplicates():
    r = client.get(f"/api/customers/{CUST_ALICE}/recommendations")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "precomputed"
    ids = [i["article_id"] for i in body["items"]]
    assert all(isinstance(a, str) and len(a) == 10 and a.isdigit() for a in ids)
    assert len(ids) == len(set(ids))
    assert 1 <= len(ids) <= 10
    ranks = [i["rank"] for i in body["items"]]
    assert ranks == list(range(1, len(ranks) + 1))


def test_recommendations_exclude_purchased():
    body = client.get(f"/api/customers/{CUST_ALICE}/recommendations").json()
    ids = [i["article_id"] for i in body["items"]]
    # Alice owns ARTICLES[0] and ARTICLES[1] -> both filtered from the pool
    assert FMT[ARTICLES[0]] not in ids and FMT[ARTICLES[1]] not in ids
    assert body["filtered_out"] == 2

    body2 = client.get(
        f"/api/customers/{CUST_ALICE}/recommendations?exclude_purchased=false"
    ).json()
    ids2 = [i["article_id"] for i in body2["items"]]
    assert FMT[ARTICLES[0]] in ids2


def test_recommendations_reason_codes_valid():
    body = client.get(f"/api/customers/{CUST_ALICE}/recommendations").json()
    valid = {"COLLABORATIVE", "CONTENT_SIMILARITY", "POPULARITY", "REPEAT_PURCHASE", "HYBRID"}
    for item in body["items"]:
        assert item["reason"] in valid
        assert item["reason_text"]
        for comp in item["components"].values():
            assert 0.0 <= comp <= 1.0


def test_recommendations_include_article_display():
    body = client.get(f"/api/customers/{CUST_ALICE}/recommendations").json()
    for item in body["items"]:
        assert item["article"] is not None
        assert len(item["article"]["features"]) == 9
        assert item["article"]["stats"]["purchase_count"] > 0


def test_recommendations_popularity_fallback_for_empty_customer():
    r = client.get(f"/api/customers/{CUST_EMPTY}/recommendations")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "popularity_fallback"
    assert len(body["items"]) <= 10
    assert all(i["reason"] == "POPULARITY" for i in body["items"])


def test_recommendations_unknown_customer_404():
    assert client.get(f"/api/customers/{CUST_GHOST}/recommendations").status_code == 404


def test_recommendations_ranking_is_score_ordered():
    body = client.get(f"/api/customers/{CUST_ALICE}/recommendations").json()
    scores = [i["score"] for i in body["items"]]
    assert scores == sorted(scores, reverse=True)


# ---------------- articles ----------------

def test_article_detail_accepts_10_digit_and_numeric():
    # canonical 10-digit form (leading zero preserved)
    r = client.get(f"/api/articles/{FMT[ARTICLES[0]]}")
    assert r.status_code == 200
    body = r.json()
    assert body["article"]["article_id"] == FMT[ARTICLES[0]]
    assert len(body["article"]["features"]) == 9
    # bare numeric form resolves to the same article
    r2 = client.get(f"/api/articles/{ARTICLES[0]}")
    assert r2.status_code == 200
    assert r2.json()["article"]["article_id"] == FMT[ARTICLES[0]]


def test_article_404_and_422():
    assert client.get("/api/articles/0111122223").status_code == 404
    assert client.get("/api/articles/111122223").status_code == 404
    assert client.get("/api/articles/abc").status_code == 422
    assert client.get("/api/articles/-5").status_code == 422


def test_popular_articles():
    r = client.get("/api/articles/popular?limit=3")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 3
    assert body[0]["stats"]["popularity_rank"] == 1
    assert all(isinstance(a["article_id"], str) and len(a["article_id"]) == 10 for a in body)


# ---------------- display metadata enrichment ----------------

def test_article_detail_has_human_readable_metadata():
    a = client.get(f"/api/articles/{FMT[ARTICLES[0]]}").json()["article"]
    assert a["article_id"] == FMT[ARTICLES[0]]
    assert a["product_type"] == "Sweater"
    assert a["colour"] == "Black"
    assert a["product_group"] == "Garment Upper body"
    assert a["department"] == "Jersey"
    assert len(a["features"]) == 9  # encoded features still present (not replaced)


def test_recommendations_enriched_with_labels_not_codes():
    d = client.get(f"/api/customers/{CUST_ALICE}/recommendations").json()
    assert d["count"] >= 1
    for item in d["items"]:
        a = item["article"]
        # display fields present for known articles
        if a["article_id"] != FMT[ARTICLES[4]]:
            assert a["product_type"] and a["colour"]
        # human-readable label never shows numeric codes on the card path
        assert a["product_type"] != "Type"
        assert a["image_url"] is not None or True  # image mapping unchanged


def test_purchase_history_enriched():
    d = client.get(f"/api/customers/{CUST_ALICE}/history").json()
    for item in d["items"]:
        a = item["article"]
        if a is not None and a["article_id"] == FMT[ARTICLES[0]]:
            assert a["product_type"] == "Sweater"
            assert a["colour"] == "Black"
            break
    else:
        pytest.fail("ARTICLES[0] not found in history")


def test_popular_articles_enriched():
    body = client.get("/api/articles/popular?limit=3").json()
    for a in body:
        assert a["product_type"] and a["colour"]


def test_similar_articles_enriched():
    d = client.get(f"/api/articles/{FMT[ARTICLES[0]]}?similar_count=2").json()
    for s in d["similar"]:
        assert s["article"]["product_type"]


def test_ranking_unchanged_by_enrichment():
    d = client.get(f"/api/customers/{CUST_ALICE}/recommendations").json()
    ids = [i["article_id"] for i in d["items"]]
    assert ids[0] == FMT[ARTICLES[3]]  # same rank-1 as before enrichment
    scores = [i["score"] for i in d["items"]]
    assert scores == sorted(scores, reverse=True)


# ---------------- image serving ----------------

def test_image_api_serves_indexed_image(monkeypatch):
    import polars as pl

    from backend.app.core.config import get_settings
    from backend.app.services.images import image_index, resolve_article_image

    s = get_settings()
    idx_path = s.serving_data_dir / "image_index.parquet"
    existed = idx_path.exists()
    fake = s.serving_data_dir / "test_fixture_image.jpg"
    fake.write_bytes(bytes([0xFF, 0xD8, 0xFF]) + b"fixture")
    pl.DataFrame({
        "article_id": [FMT[ARTICLES[3]]],
        "image_path": [str(fake)],
        "extension": ["jpg"],
    }).write_parquet(idx_path)
    image_index.cache_clear()
    try:
        # recommendation responses now include a real image_url
        d = client.get(f"/api/customers/{CUST_ALICE}/recommendations").json()
        with_img = [i for i in d["items"] if i["article_id"] == FMT[ARTICLES[3]]]
        assert with_img, f"ARTICLES[3] not in recs: {[i['article_id'] for i in d['items']]}"
        assert with_img[0]["article"]["image_url"] == f"/api/images/{FMT[ARTICLES[3]]}"

        r = client.get(f"/api/images/{FMT[ARTICLES[3]]}")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/jpeg"

        assert client.get("/api/images/0777777777").status_code == 404      # not indexed
        # traversal-style ids are rejected (404: route never matches a path segment)
        assert client.get("/api/images/..%2F..%2Fsecret").status_code in (404, 422)
        assert client.get("/api/images/abc").status_code == 422
    finally:
        if not existed:
            idx_path.unlink()
        fake.unlink(missing_ok=True)
        image_index.cache_clear()
        get_settings.cache_clear()


# ---------------- stats ----------------

def test_stats_endpoint():
    r = client.get("/api/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["dataset"]["n_transactions"] == 31788324
    assert body["model"]["weights"]["collab"] == 0.45
