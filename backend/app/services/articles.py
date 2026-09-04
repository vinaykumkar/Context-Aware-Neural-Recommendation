"""Article display + lookup services.

The cleaned ML dataset stores article attributes as label-encoded indices
(no human-readable names are available in the source data), so display data
is honest about that: codes are surfaced as e.g. ``Type #33`` together with
real demand statistics. No names are fabricated.
"""
from __future__ import annotations

import duckdb

from ..core.article_id import format_article_id, parse_article_id
from ..core.store import connection, require
from ..services.images import resolve_article_image

ARTICLE_FEATURES = [
    "product_type_name_index",
    "product_group_name_index",
    "graphical_appearance_name_index",
    "colour_group_name_index",
    "department_name_index",
    "index_name_index",
    "index_group_name_index",
    "section_name_index",
    "garment_group_name_index",
]

_LABEL_BY_FEATURE = {
    "product_type_name_index": "Type",
    "product_group_name_index": "Group",
    "graphical_appearance_name_index": "Appearance",
    "colour_group_name_index": "Colour",
    "department_name_index": "Department",
    "index_name_index": "Index",
    "index_group_name_index": "Index group",
    "section_name_index": "Section",
    "garment_group_name_index": "Garment group",
}

SELECT_DISPLAY = """
    a.article_id,
    d.product_type_name,
    d.product_group_name,
    d.colour_group_name,
    d.department_name,
    d.section_name,
    d.garment_group_name,
    d.graphical_appearance_name,
    d.index_group_name,
    d.index_name,
    a.product_type_name_index,
    a.product_group_name_index,
    a.graphical_appearance_name_index,
    a.colour_group_name_index,
    a.department_name_index,
    a.index_name_index,
    a.index_group_name_index,
    a.section_name_index,
    a.garment_group_name_index,
    COALESCE(a.purchase_count, 0)       AS purchase_count,
    COALESCE(a.unique_customers, 0)     AS unique_customers,
    a.avg_price,
    a.first_sale_date,
    a.last_sale_date,
    COALESCE(a.sales_last_28d, 0)       AS sales_last_28d,
    COALESCE(a.sales_last_84d, 0)       AS sales_last_84d,
    p.popularity_rank
"""


def article_row_to_dict(r: dict) -> dict:
    """Convert a DuckDB row (dict form) into the article display payload."""
    if r is None:
        return {}
    features = [
        {"feature": _LABEL_BY_FEATURE[c], "code": int(r[c])}
        for c in ARTICLE_FEATURES
        if r.get(c) is not None
    ]
    return {
        "article_id": format_article_id(r["article_id"]),
        "features": features,
        "stats": {
            "purchase_count": int(r.get("purchase_count") or 0),
            "unique_customers": int(r.get("unique_customers") or 0),
            "avg_price": r.get("avg_price"),
            "first_sale_date": str(r["first_sale_date"]) if r.get("first_sale_date") else None,
            "last_sale_date": str(r["last_sale_date"]) if r.get("last_sale_date") else None,
            "sales_last_28d": int(r.get("sales_last_28d") or 0),
            "sales_last_84d": int(r.get("sales_last_84d") or 0),
            "popularity_rank": int(r["popularity_rank"]) if r.get("popularity_rank") else None,
        },
        "image_url": resolve_article_image(r["article_id"]),
        "label": None,
        "product_type": r.get("product_type_name"),
        "product_group": r.get("product_group_name"),
        "colour": r.get("colour_group_name"),
        "department": r.get("department_name"),
        "section": r.get("section_name"),
        "garment_group": r.get("garment_group_name"),
        "graphical_appearance": r.get("graphical_appearance_name"),
        "index_group": r.get("index_group_name"),
        "index_name": r.get("index_name"),
    }


def get_articles_by_ids(article_ids: list[int]) -> dict[int, dict]:
    """Fetch display data for a batch of articles (single small query)."""
    require(articles=True)
    if not article_ids:
        return {}
    con: duckdb.DuckDBPyConnection = connection()
    ids = ",".join(str(int(i)) for i in set(article_ids))  # ints validated upstream
    rows = con.execute(
        f"""
        SELECT {SELECT_DISPLAY}
        FROM articles_serving a
        LEFT JOIN article_popularity p USING (article_id)
        LEFT JOIN articles_display d USING (article_id)
        WHERE a.article_id IN ({ids})
        """
    ).fetchdf().to_dict(orient="records")
    return {int(r["article_id"]): article_row_to_dict(r) for r in rows}


def display_available() -> bool:
    """True when the display serving table exists (enrichment possible)."""
    con = connection()
    try:
        con.execute("SELECT 1 FROM articles_display LIMIT 1")
        return True
    except Exception:
        return False


def article_exists(article_id: int | str) -> bool:
    v = parse_article_id(article_id)
    if v is None:
        return False
    require(articles=True)
    con = connection()
    n = con.execute(
        "SELECT COUNT(*) FROM articles_serving WHERE article_id = ?", [v]
    ).fetchone()
    return bool(n and n[0] > 0)
