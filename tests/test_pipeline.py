"""Unit tests for pipeline helpers and services (no real dataset needed)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.core.article_id import (  # noqa: E402
    format_article_id,
    is_valid_article_id,
    parse_article_id,
)

from backend.app.core.config import get_settings  # noqa: E402
from backend.app.core.serving import customer_bucket  # noqa: E402
from backend.app.services.images import find_image_file, image_mode, resolve_article_image  # noqa: E402
from backend.app.services.recommendations import diversity_filter  # noqa: E402
from scripts.pipeline.build_recs import dominant_reason  # noqa: E402
from backend.app.schemas import RecommendationItem  # noqa: E402


# ---------------- canonical article id formatting ----------------

def test_format_article_id_known_cases():
    assert format_article_id(800691008) == "0800691008"
    assert format_article_id(706016001) == "0706016001"
    assert format_article_id(123456789) == "0123456789"


def test_format_article_id_accepts_both_forms():
    assert format_article_id("800691008") == "0800691008"
    assert format_article_id("0800691008") == "0800691008"
    assert format_article_id(" 663713001 ") == "0663713001"


def test_format_article_id_always_ten_digits():
    for v in (1, 999999, 663713001, 2147483647):
        out = format_article_id(v)
        assert len(out) == 10 and out.isdigit()


def test_format_article_id_rejects_malformed():
    import pytest
    for bad in ("abc", "-5", "0", "", "12345678901", None, 12.5):
        with pytest.raises(ValueError):
            format_article_id(bad)
    assert parse_article_id("abc") is None
    assert parse_article_id(-5) is None
    assert parse_article_id("12345678901") is None
    assert is_valid_article_id("0800691008")
    assert not is_valid_article_id("")


# ---------------- image index resolution ----------------

def test_image_index_resolution(monkeypatch, tmp_path):
    """The prebuilt index resolves images without IMAGE_DIR."""
    import polars as pl

    from backend.app.services import images as img_mod

    s = get_settings()
    idx_path = s.serving_data_dir / "image_index.parquet"
    existed = idx_path.exists()
    fake = s.serving_data_dir / "test_fixture_image.jpg"
    fake.write_bytes(b"fake-bytes")
    pl.DataFrame({
        "article_id": ["0800691008", "0111111111"],
        "image_path": [str(fake), str(s.serving_data_dir / "missing.jpg")],
        "extension": ["jpg", "jpg"],
    }).write_parquet(idx_path)
    img_mod.image_index.cache_clear()
    try:
        assert img_mod.image_mode() == "local"
        assert resolve_article_image("0800691008") == "/api/images/0800691008"
        assert resolve_article_image(800691008) == "/api/images/0800691008"  # leading zero preserved
        assert find_image_file("0800691008") == fake
        assert resolve_article_image("0111111111") is None   # index row whose file is gone
        assert resolve_article_image("0777777777") is None   # not in index
    finally:
        if not existed:
            idx_path.unlink()
        fake.unlink(missing_ok=True)
        img_mod.image_index.cache_clear()
        get_settings.cache_clear()


# ---------------- bucketing ----------------

def test_customer_bucket_is_stable():
    cid = "a" * 60 + "00000001"
    assert customer_bucket(cid) == customer_bucket(cid)
    import zlib
    assert customer_bucket(cid) == zlib.crc32(cid.encode()) % get_settings().num_buckets


def test_customer_bucket_in_range():
    for i in range(50):
        b = customer_bucket(f"{i:064x}")
        assert 0 <= b < get_settings().num_buckets


def test_buckets_are_reasonably_spread():
    counts = [0] * get_settings().num_buckets
    for i in range(400):
        counts[customer_bucket(f"{i:064x}")] += 1
    assert max(counts) <= 0.6 * 400  # not all in one bucket


# ---------------- reason codes ----------------

def test_dominant_reason_collab_wins():
    codes = dominant_reason(
        np.array([0.9]), np.array([0.2]), np.array([0.1]), np.array([0.0])
    )
    assert codes[0] == "COLLABORATIVE"


def test_dominant_reason_popularity_for_cold_start():
    codes = dominant_reason(
        np.array([0.0]), np.array([0.0]), np.array([0.8]), np.array([0.0])
    )
    assert codes[0] == "POPULARITY"


def test_dominant_reason_hybrid_when_close():
    # inverse-weight inputs produce equal weighted contributions -> HYBRID
    codes = dominant_reason(
        np.array([1 / 0.45]), np.array([1 / 0.25]), np.array([1 / 0.20]), np.array([1 / 0.10])
    )
    assert codes[0] == "HYBRID"


# ---------------- diversity filter ----------------

def _item(article_id: int) -> RecommendationItem:
    from backend.app.schemas import ComponentScores

    return RecommendationItem(
        rank=1,
        article_id=format_article_id(article_id),
        score=1.0,
        components=ComponentScores(collaborative=0, content=0, popularity=0, repurchase=0),
        reason="HYBRID",
        reason_text="x",
    )


def test_diversity_filter_caps_same_group(monkeypatch, tmp_path):
    # articles_serving from the fixture: ids 0,1 share group 6; id 2 group 0 etc.
    from backend.app.core.store import connection

    con = connection()
    # groups of the fixture articles: ARTICLES = [663713001, 541518023, 505221004, ...]
    items = [_item(663713001), _item(541518023), _item(505221004), _item(767541003), _item(902106001)]
    # fixture product_group values cycle [6,3,0,6,3,...] -> indices 0 and 3 share group 6
    kept = diversity_filter(items, max_per_group=1)
    kept_ids = {i.article_id for i in kept}
    assert not ({663713001, 767541003} <= kept_ids)  # both group-6 items can't survive cap=1


# ---------------- images ----------------

def test_placeholder_mode_when_unconfigured():
    assert image_mode() == "placeholder"
    assert resolve_article_image(663713001) is None


def test_image_id_validation():
    assert resolve_article_image(663713001) is None  # no provider configured
    assert resolve_article_image(-5) is None
    assert resolve_article_image(12345678901234) is None


def test_local_image_provider(monkeypatch, tmp_path):
    img_dir = tmp_path / "images"
    (img_dir / "066").mkdir(parents=True)  # canonical subfolder layout
    (img_dir / "066" / "0663713001.jpg").write_bytes(b"fake")
    monkeypatch.setenv("IMAGE_DIR", str(img_dir))
    get_settings.cache_clear()
    try:
        assert image_mode() == "local"
        assert resolve_article_image(663713001) == "/api/images/0663713001"
        assert resolve_article_image("0663713001") == "/api/images/0663713001"
        assert find_image_file(663713001) == img_dir / "066" / "0663713001.jpg"
        assert resolve_article_image(541518023) is None
    finally:
        monkeypatch.delenv("IMAGE_DIR")
        get_settings.cache_clear()


def test_local_image_provider_flat_layouts(monkeypatch, tmp_path):
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    (img_dir / "0541518023.jpg").write_bytes(b"flat")  # flat canonical name
    monkeypatch.setenv("IMAGE_DIR", str(img_dir))
    get_settings.cache_clear()
    try:
        assert find_image_file("0541518023") == img_dir / "0541518023.jpg"
        assert find_image_file(541518023) == img_dir / "0541518023.jpg"
    finally:
        monkeypatch.delenv("IMAGE_DIR")
        get_settings.cache_clear()


def test_url_template_provider(monkeypatch):
    monkeypatch.setenv(
        "IMAGE_URL_TEMPLATE",
        "https://cdn.example.com/{article_id}.jpg?raw={article_id_raw}",
    )
    get_settings.cache_clear()
    try:
        assert image_mode() == "url_template"
        assert (
            resolve_article_image(663713001)
            == "https://cdn.example.com/0663713001.jpg?raw=663713001"
        )
    finally:
        monkeypatch.delenv("IMAGE_URL_TEMPLATE")
        get_settings.cache_clear()
