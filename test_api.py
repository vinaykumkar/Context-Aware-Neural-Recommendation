"""API tests for the synthetic recommendation-serving fixture."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Make project root importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
from tests.conftest import (
    ARTICLES,
    CUST_ALICE,
    CUST_BOB,
    CUST_EMPTY,
    CUST_GHOST,
)

client = TestClient(app)

# Canonical H&M-style 10-digit article IDs
ARTICLE_IDS = {article_id: f"{article_id:010d}" for article_id in ARTICLES}


# ============================================================
# HEALTH & CONFIG
# ============================================================

def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["serving"]["customers_serving"] is True
    assert data["serving"]["recommendation_buckets"] == 4


def test_configuration_endpoint():
    response = client.get("/api/config")

    assert response.status_code == 200

    data = response.json()

    assert data["image_mode"] == "placeholder"
    assert data["max_recommendation_count"] == 50


# ============================================================
# CUSTOMER APIs
# ============================================================

def test_customer_pagination():
    response = client.get(
        "/api/customers",
        params={"page": 1, "page_size": 2},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["pages"] == 2


def test_customer_search():
    response = client.get(
        "/api/customers",
        params={"q": "a" * 12},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["customer_id"] == CUST_ALICE


def test_customers_without_purchases():
    response = client.get(
        "/api/customers",
        params={"has_purchases": False},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["customer_id"] == CUST_EMPTY


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 1000},
    ],
)
def test_invalid_customer_pagination(params):
    response = client.get("/api/customers", params=params)

    assert response.status_code == 422


# ============================================================
# CUSTOMER PROFILE
# ============================================================

def test_customer_profile():
    response = client.get(f"/api/customers/{CUST_ALICE}")

    assert response.status_code == 200

    data = response.json()

    assert data["customer"]["purchase_count"] == 4
    assert data["customer"]["short_id"].endswith("0001")
    assert len(data["top_categories"]) == 5


def test_unknown_customer_profile():
    response = client.get(f"/api/customers/{CUST_GHOST}")

    assert response.status_code == 404


def test_customer_without_purchase_history():
    response = client.get(f"/api/customers/{CUST_EMPTY}")

    assert response.status_code == 200

    data = response.json()

    assert data["customer"]["has_purchases"] is False
    assert data["top_categories"] == []


def test_invalid_customer_id():
    response = client.get("/api/customers/not-hex")

    assert response.status_code == 422


# ============================================================
# PURCHASE HISTORY
# ============================================================

def test_customer_history():
    response = client.get(
        f"/api/customers/{CUST_ALICE}/history"
    )

    assert response.status_code == 200

    data = response.json()

    dates = [item["t_dat"] for item in data["items"]]

    assert dates == sorted(dates, reverse=True)
    assert data["total_transactions"] == 4

    first_item = data["items"][0]

    assert first_item["article_id"] == ARTICLE_IDS[ARTICLES[0]]
    assert isinstance(first_item["article_id"], str)

    assert (
        first_item["article"]["article_id"]
        == ARTICLE_IDS[ARTICLES[0]]
    )

    assert first_item["article"]["image_url"] is None


def test_history_limit():
    response = client.get(
        f"/api/customers/{CUST_ALICE}/history",
        params={"limit": 2},
    )

    assert response.status_code == 200
    assert response.json()["returned"] == 2


def test_empty_customer_history():
    response = client.get(
        f"/api/customers/{CUST_EMPTY}/history"
    )

    assert response.status_code == 200
    assert response.json()["returned"] == 0


# ============================================================
# RECOMMENDATIONS
# ============================================================

def get_recommendations(customer_id=CUST_ALICE, **params):
    response = client.get(
        f"/api/customers/{customer_id}/recommendations",
        params=params,
    )

    assert response.status_code == 200

    return response.json()


def test_recommendation_structure():
    data = get_recommendations()

    assert data["source"] == "precomputed"

    article_ids = [
        item["article_id"]
        for item in data["items"]
    ]

    assert all(
        isinstance(article_id, str)
        and len(article_id) == 10
        and article_id.isdigit()
        for article_id in article_ids
    )

    assert len(article_ids) == len(set(article_ids))
    assert 1 <= len(article_ids) <= 10


def test_recommendation_ranks():
    data = get_recommendations()

    ranks = [
        item["rank"]
        for item in data["items"]
    ]

    assert ranks == list(range(1, len(ranks) + 1))


def test_recommendations_exclude_purchased_items():
    data = get_recommendations()

    article_ids = {
        item["article_id"]
        for item in data["items"]
    }

    assert ARTICLE_IDS[ARTICLES[0]] not in article_ids
    assert ARTICLE_IDS[ARTICLES[1]] not in article_ids
    assert data["filtered_out"] == 2


def test_recommendations_can_include_purchased_items():
    data = get_recommendations(
        exclude_purchased=False
    )

    article_ids = {
        item["article_id"]
        for item in data["items"]
    }

    assert ARTICLE_IDS[ARTICLES[0]] in article_ids


def test_recommendation_reasons():
    data = get_recommendations()

    valid_reasons = {
        "COLLABORATIVE",
        "CONTENT_SIMILARITY",
        "POPULARITY",
        "REPEAT_PURCHASE",
        "HYBRID",
    }

    for item in data["items"]:
        assert item["reason"] in valid_reasons
        assert item["reason_text"]

        for value in item["components"].values():
            assert 0.0 <= value <= 1.0


def test_recommendations_contain_article_information():
    data = get_recommendations()

    for item in data["items"]:
        article = item["article"]

        assert article is not None
        assert len(article["features"]) == 9
        assert article["stats"]["purchase_count"] > 0


def test_empty_customer_uses_popularity_fallback():
    data = get_recommendations(CUST_EMPTY)

    assert data["source"] == "popularity_fallback"
    assert len(data["items"]) <= 10

    assert all(
        item["reason"] == "POPULARITY"
        for item in data["items"]
    )


def test_unknown_customer_recommendations():
    response = client.get(
        f"/api/customers/{CUST_GHOST}/recommendations"
    )

    assert response.status_code == 404


def test_recommendations_sorted_by_score():
    data = get_recommendations()

    scores = [
        item["score"]
        for item in data["items"]
    ]

    assert scores == sorted(scores, reverse=True)


# ============================================================
# ARTICLE APIs
# ============================================================

def test_article_accepts_canonical_id():
    article_id = ARTICLE_IDS[ARTICLES[0]]

    response = client.get(
        f"/api/articles/{article_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["article"]["article_id"] == article_id
    assert len(data["article"]["features"]) == 9


def test_article_accepts_numeric_id():
    article_id = ARTICLES[0]

    response = client.get(
        f"/api/articles/{article_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["article"]["article_id"] == ARTICLE_IDS[ARTICLES[0]]


@pytest.mark.parametrize(
    "article_id, expected_status",
    [
        ("0111122223", 404),
        ("111122223", 404),
        ("abc", 422),
        ("-5", 422),
    ],
)
def test_invalid_article_ids(article_id, expected_status):
    response = client.get(
        f"/api/articles/{article_id}"
    )

    assert response.status_code == expected_status


def test_popular_articles():
    response = client.get(
        "/api/articles/popular",
        params={"limit": 3},
    )

    assert response.status_code == 200

    articles = response.json()

    assert len(articles) == 3
    assert articles[0]["stats"]["popularity_rank"] == 1

    assert all(
        isinstance(article["article_id"], str)
        and len(article["article_id"]) == 10
        for article in articles
    )


# ============================================================
# ARTICLE METADATA
# ============================================================

def test_article_metadata():
    article_id = ARTICLE_IDS[ARTICLES[0]]

    data = client.get(
        f"/api/articles/{article_id}"
    ).json()

    article = data["article"]

    assert article["product_type"] == "Sweater"
    assert article["colour"] == "Black"
    assert article["product_group"] == "Garment Upper body"
    assert article["department"] == "Jersey"
    assert len(article["features"]) == 9


def test_recommendations_have_readable_metadata():
    data = get_recommendations()

    for item in data["items"]:
        article = item["article"]

        if article["article_id"] != ARTICLE_IDS[ARTICLES[4]]:
            assert article["product_type"]
            assert article["colour"]

        assert article["product_type"] != "Type"


def test_history_contains_readable_article_metadata():
    data = client.get(
        f"/api/customers/{CUST_ALICE}/history"
    ).json()

    found = False

    for item in data["items"]:
        article = item["article"]

        if (
            article is not None
            and article["article_id"] == ARTICLE_IDS[ARTICLES[0]]
        ):
            assert article["product_type"] == "Sweater"
            assert article["colour"] == "Black"
            found = True
            break

    assert found


def test_popular_articles_have_metadata():
    articles = client.get(
        "/api/articles/popular",
        params={"limit": 3},
    ).json()

    for article in articles:
        assert article["product_type"]
        assert article["colour"]


def test_similar_articles_have_metadata():
    article_id = ARTICLE_IDS[ARTICLES[0]]

    data = client.get(
        f"/api/articles/{article_id}",
        params={"similar_count": 2},
    ).json()

    for similar in data["similar"]:
        assert similar["article"]["product_type"]


def test_enrichment_does_not_change_ranking():
    data = get_recommendations()

    ids = [
        item["article_id"]
        for item in data["items"]
    ]

    scores = [
        item["score"]
        for item in data["items"]
    ]

    assert ids[0] == ARTICLE_IDS[ARTICLES[3]]
    assert scores == sorted(scores, reverse=True)


# ============================================================
# IMAGE API
# ============================================================

def test_image_endpoint(monkeypatch):
    import polars as pl

    from backend.app.core.config import get_settings
    from backend.app.services.images import (
        image_index,
    )

    settings = get_settings()

    index_path = (
        settings.serving_data_dir
        / "image_index.parquet"
    )

    existed_before = index_path.exists()

    fake_image = (
        settings.serving_data_dir
        / "test_fixture_image.jpg"
    )

    fake_image.write_bytes(
        bytes([0xFF, 0xD8, 0xFF]) + b"fixture"
    )

    pl.DataFrame(
        {
            "article_id": [ARTICLE_IDS[ARTICLES[3]]],
            "image_path": [str(fake_image)],
            "extension": ["jpg"],
        }
    ).write_parquet(index_path)

    image_index.cache_clear()

    try:
        data = get_recommendations()

        matching = [
            item
            for item in data["items"]
            if item["article_id"]
            == ARTICLE_IDS[ARTICLES[3]]
        ]

        assert matching

        assert (
            matching[0]["article"]["image_url"]
            == f"/api/images/{ARTICLE_IDS[ARTICLES[3]]}"
        )

        response = client.get(
            f"/api/images/{ARTICLE_IDS[ARTICLES[3]]}"
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"

        assert client.get(
            "/api/images/0777777777"
        ).status_code == 404

        assert client.get(
            "/api/images/abc"
        ).status_code == 422

    finally:
        if not existed_before:
            index_path.unlink(missing_ok=True)

        fake_image.unlink(missing_ok=True)

        image_index.cache_clear()
        get_settings.cache_clear()


# ============================================================
# STATISTICS & FILTERS
# ============================================================

def test_average_order_value():
    response = client.get("/api/stats/aov")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data["months"], list)
    assert data["order_definition"]

    months = data["months"]

    assert all(
        len(month["month"]) == 7
        for month in months
    )

    for month in months:
        expected_aov = round(
            month["total_revenue"]
            / month["total_orders"],
            6,
        )

        assert (
            month["average_order_value"]
            == expected_aov
        )

    dates = [month["month"] for month in months]

    assert dates == sorted(dates)


def test_filter_options():
    response = client.get("/api/stats/filters")

    assert response.status_code == 200

    data = response.json()

    assert "under_18" in data["age_bands"]
    assert "55_plus" in data["age_bands"]

    assert data["divisions"]
    assert data["departments"]


def test_invalid_age_band():
    response = client.get(
        f"/api/customers/{CUST_ALICE}/recommendations",
        params={"age_band": 99},
    )

    assert response.status_code == 422


def test_department_filter():
    data = get_recommendations(
        count=50,
        department="Jersey",
    )

    for item in data["items"]:
        assert item["article"]["department"] == "Jersey"


def test_gender_filter():
    data = get_recommendations(
        count=50,
        gender="Ladieswear",
    )

    for item in data["items"]:
        assert item["article"]["index_group"] == "Ladieswear"


def test_multiple_filters():
    data = get_recommendations(
        count=50,
        gender="Ladieswear",
        department="Jersey",
    )

    for item in data["items"]:
        article = item["article"]

        assert article["index_group"] == "Ladieswear"
        assert article["department"] == "Jersey"


# ============================================================
# DATASET STATISTICS
# ============================================================

def test_dataset_statistics():
    response = client.get("/api/stats")

    assert response.status_code == 200

    data = response.json()

    assert data["dataset"]["n_transactions"] == 31788324
    assert data["model"]["weights"]["collab"] == 0.45
