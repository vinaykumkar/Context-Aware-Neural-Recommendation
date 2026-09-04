"""Canonical article-id handling.

The cleaned dataset stores ``article_id`` as an integer, so the leading zero
of the original 10-digit H&M article id is lost (e.g. stored ``800691008``,
original ``0800691008``).

Convention across the whole project:

* INTERNAL (parquet keys, joins, models, recommendation buckets):
  numeric ``int`` — never changed, matches the generated data.
* EXTERNAL (API responses, UI display, image lookup, URLs, clipboard):
  the canonical 10-digit zero-padded STRING produced by :func:`format_article_id`.

This module is the single source of that formatting logic.
"""
from __future__ import annotations

import re

# 1..10 digits, positive — covers numeric storage forms and the 10-digit form
_ARTICLE_ID_RE = re.compile(r"^\d{1,10}$")
# internal storage is int32
_MAX_INT32 = 2_147_483_647
WIDTH = 10


def parse_article_id(value: int | str) -> int | None:
    """Normalize int / numeric-string input to the internal integer id.

    Accepts ``800691008`` and ``"0800691008"`` alike. Returns ``None`` for
    malformed values (non-numeric, negative, overflowing int32).
    """
    s = str(value).strip()
    if not _ARTICLE_ID_RE.match(s):
        return None
    v = int(s)
    if v <= 0 or v > _MAX_INT32:
        return None
    return v


def format_article_id(value: int | str) -> str:
    """Canonical external representation: exactly 10 digits, zero-padded.

    >>> format_article_id(800691008)
    '0800691008'
    >>> format_article_id("706016001")
    '0706016001'
    >>> format_article_id(123456789)
    '0123456789'
    """
    v = parse_article_id(value)
    if v is None:
        raise ValueError(f"invalid article id: {value!r}")
    return str(v).zfill(WIDTH)


def is_valid_article_id(value: int | str) -> bool:
    return parse_article_id(value) is not None
