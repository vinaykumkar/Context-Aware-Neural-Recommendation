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


def search_articles(
    con: duckdb.DuckDBPyConnection,
    q: str | None = None,
    gender: str | None = None,
    product_group: str | None = None,
    age_group: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str = "popularity",
    page: int = 1,
    page_size: int = 24,
) -> dict:
    require(articles=True)
    where_clauses = ["COALESCE(a.purchase_count, 0) > 0"]
    params: list = []

    if q:
        q_clean = q.strip().lower()
        where_clauses.append(
            """(
                CAST(a.article_id AS VARCHAR) LIKE ?
                OR LOWER(COALESCE(d.product_type_name, '')) LIKE ?
                OR LOWER(COALESCE(d.product_group_name, '')) LIKE ?
                OR LOWER(COALESCE(d.department_name, '')) LIKE ?
                OR LOWER(COALESCE(d.index_group_name, '')) LIKE ?
                OR LOWER(COALESCE(d.colour_group_name, '')) LIKE ?
            )"""
        )
        pattern = f"%{q_clean}%"
        params.extend([pattern] * 6)

    if gender:
        g_clean = gender.strip().lower()
        where_clauses.append("LOWER(COALESCE(d.index_group_name, '')) = ?")
        params.append(g_clean)

    if product_group:
        pg_clean = product_group.strip().lower()
        where_clauses.append("LOWER(COALESCE(d.product_group_name, '')) = ?")
        params.append(pg_clean)

    if age_group:
        ag = age_group.strip().lower()
        if ag == "18-25":
            where_clauses.append("(LOWER(COALESCE(d.index_group_name, '')) = 'divided' OR LOWER(COALESCE(d.section_name, '')) LIKE '%divided%' OR LOWER(COALESCE(d.department_name, '')) LIKE '%young%')")
        elif ag == "26-35":
            where_clauses.append("(LOWER(COALESCE(d.index_group_name, '')) IN ('ladieswear', 'menswear', 'divided', 'sport') AND LOWER(COALESCE(d.index_group_name, '')) != 'baby/children')")
        elif ag in ("36-50", "51-100"):
            where_clauses.append("(LOWER(COALESCE(d.index_group_name, '')) IN ('ladieswear', 'menswear') AND LOWER(COALESCE(d.index_group_name, '')) != 'baby/children')")
        elif "baby" in ag or "child" in ag:
            where_clauses.append("(LOWER(COALESCE(d.index_group_name, '')) = 'baby/children' OR LOWER(COALESCE(d.department_name, '')) LIKE '%baby%' OR LOWER(COALESCE(d.department_name, '')) LIKE '%kids%')")

    if min_price is not None:
        where_clauses.append("a.avg_price >= ?")
        params.append(min_price)

    if max_price is not None:
        where_clauses.append("a.avg_price <= ?")
        params.append(max_price)

    where_sql = " AND ".join(where_clauses)

    count_sql = f"""
        SELECT COUNT(*)
        FROM articles_serving a
        LEFT JOIN articles_display d USING (article_id)
        WHERE {where_sql}
    """
    total = con.execute(count_sql, params).fetchone()[0]

    order_map = {
        "popularity": "COALESCE(p.popularity_rank, 999999) ASC",
        "price_asc": "COALESCE(a.avg_price, 999999) ASC",
        "price_desc": "COALESCE(a.avg_price, 0) DESC",
        "purchase_count": "COALESCE(a.purchase_count, 0) DESC",
        "recency": "COALESCE(a.sales_last_28d, 0) DESC, COALESCE(a.purchase_count, 0) DESC",
    }
    order_by = order_map.get(sort, "COALESCE(p.popularity_rank, 999999) ASC")

    offset = (page - 1) * page_size
    query_sql = f"""
        SELECT {SELECT_DISPLAY}
        FROM articles_serving a
        LEFT JOIN article_popularity p USING (article_id)
        LEFT JOIN articles_display d USING (article_id)
        WHERE {where_sql}
        ORDER BY {order_by}
        LIMIT {int(page_size)} OFFSET {int(offset)}
    """
    rows = con.execute(query_sql, params).fetchdf().to_dict(orient="records")
    items = [article_row_to_dict(r) for r in rows]

    import math
    pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }
