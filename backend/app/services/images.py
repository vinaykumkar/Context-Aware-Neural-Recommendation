"""Central product-image resolution.

Resolution order (all validated through ``core.article_id``):

1. LOCAL: ``IMAGE_DIR`` points at the H&M images folder (read-only). Files are
   resolved deterministically from the canonical 10-digit id
   (``{IMAGE_DIR}/080/0800691008.jpg``) with a one-stat existence check, then
   via the prebuilt index (``serving_data/image_index.parquet``) as the
   reliable source of truth. The directory is NEVER scanned at request time.
2. URL TEMPLATE: ``IMAGE_URL_TEMPLATE`` for a cloud/CDN host
   (``{article_id}`` = 10-digit form, ``{article_id_raw}`` = bare numeric).
3. neither available -> ``None``; clients render the editorial placeholder.

The browser never receives raw filesystem paths — images are served through
``/api/images/{article_id}``, which validates the id and returns only files
that resolve through this module.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from ..core.article_id import WIDTH, format_article_id, parse_article_id
from ..core.config import get_settings

logger = logging.getLogger("hm-recommender.images")

_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


@lru_cache(maxsize=1)
def image_index() -> dict[str, str]:
    """article_id (10-digit str) -> absolute image path. Loaded once."""
    path = get_settings().serving_data_dir / "image_index.parquet"
    if not path.exists():
        logger.info("no image index at %s — image lookups fall back to IMAGE_DIR/placeholder", path)
        return {}
    import polars as pl

    df = pl.read_parquet(path, columns=["article_id", "image_path"])
    index = dict(zip(df["article_id"].to_list(), df["image_path"].to_list()))
    logger.info("image index loaded: %s entries", len(index))
    return index


def _candidate_files(image_dir: Path, v: int) -> list[Path]:
    padded = str(v).zfill(WIDTH)
    prefix = padded[:3]
    exts = list(_IMAGE_EXTENSIONS)
    names = [f"{prefix}/{padded}", padded, str(v)]  # canonical subfolder, flat canonical, legacy numeric
    return [image_dir / f"{n}{e}" for n in names for e in exts]


def find_image_file(article_id: int | str) -> Path | None:
    """Locate the image file on disk (deterministic path first, index fallback)."""
    s = get_settings()
    v = parse_article_id(article_id)
    if v is None:
        return None
    if s.image_dir is not None:
        for candidate in _candidate_files(s.image_dir, v):
            if candidate.is_file():
                return candidate
    mapped = image_index().get(format_article_id(v))
    if mapped:
        p = Path(mapped)
        if p.is_file():
            return p
    return None


def resolve_article_image(article_id: int | str) -> str | None:
    """Return a browser-usable image URL for the article, or None (placeholder).

    ``find_image_file`` guarantees the file actually exists (deterministic
    path first, index second) — so a returned URL is always servable.
    """
    s = get_settings()
    v = parse_article_id(article_id)
    if v is None:
        return None
    if find_image_file(v) is not None:
        return f"/api/images/{format_article_id(v)}"
    if s.image_url_template:
        return s.image_url_template.format(
            article_id=format_article_id(v), article_id_raw=v
        )
    return None


def image_mode() -> str:
    s = get_settings()
    if s.image_dir is not None or image_index():
        return "local"
    if s.image_url_template:
        return "url_template"
    return "placeholder"
