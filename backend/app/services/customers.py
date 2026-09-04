"""Customer discovery, profile and history services."""
from __future__ import annotations

from duckdb import DuckDBPyConnection

from ..core.article_id import format_article_id
from ..core.store import connection, query_history, require
from ..schemas import (
    CategoryAffinity,
    CustomerListResponse,
    CustomerProfileResponse,
    CustomerSummary,
    HistoryItem,
    HistoryResponse,
)
from ..services.articles import get_articles_by_ids

SORT_COLUMNS = {
    "purchase_count": "purchase_count DESC",
    "total_spent": "total_spent DESC",
    "recency": "recency_days ASC NULLS LAST",
    "customer_id": "customer_id ASC",
}


def short_id(customer_id: str) -> str:
    return f"{customer_id[:4]}…{customer_id[-4:]}" if len(customer_id) > 12 else customer_id


def row_to_summary(r: dict) -> CustomerSummary:
    return CustomerSummary(
        customer_id=r["customer_id"],
        short_id=short_id(r["customer_id"]),
        age=r["age"],
        club_member_status=r["club_member_status"],
        fashion_news_frequency=r["fashion_news_frequency"],
        active=r["Active"],
        purchase_count=int(r.get("purchase_count") or 0),
        unique_articles_count=int(r.get("unique_articles_count") or 0),
        average_price=r["average_price"],
        total_spent=r["total_spent"],
        recency_days=r["recency_days"],
        purchase_frequency=r["purchase_frequency"],
        customer_lifetime_days=r["customer_lifetime_days"],
        has_purchases=bool(r.get("has_purchases", False)),
    )


def search_customers(
    con: DuckDBPyConnection,
    q: str | None,
    page: int,
    page_size: int,
    has_purchases: bool | None,
    sort: str,
    age_min: int | None = None,
    age_max: int | None = None,
) -> CustomerListResponse:
    require(customers=True)
    where = ["TRUE"]
    params: list = []
    if q:
        pattern = "%" + q.replace("%", "").replace("_", "") + "%"
        where.append("customer_id LIKE ?")
        params.append(pattern)
    if has_purchases is True:
        where.append("COALESCE(has_purchases, purchase_count > 0)")
    elif has_purchases is False:
        where.append("NOT COALESCE(has_purchases, purchase_count > 0)")
    if age_min is not None:
        where.append("age >= ?")
        params.append(age_min)
    if age_max is not None:
        where.append("age <= ?")
        params.append(age_max)
    order = SORT_COLUMNS.get(sort, SORT_COLUMNS["purchase_count"])
    w = " AND ".join(where)

    total = con.execute(
        f"SELECT COUNT(*) FROM customers_serving WHERE {w}", params
    ).fetchone()[0]
    offset = (page - 1) * page_size
    rows = con.execute(
        f"""
        SELECT * FROM customers_serving
        WHERE {w}
        ORDER BY {order}
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, offset],
    ).fetchdf().to_dict(orient="records")
    items = [row_to_summary(r) for r in rows]
    pages = max(1, -(-total // page_size))
    return CustomerListResponse(items=items, total=int(total), page=page, page_size=page_size, pages=pages)


def get_customer_profile(customer_id: str) -> CustomerProfileResponse:
    con = connection()
    require(customers=True)
    df = con.execute(
        "SELECT * FROM customers_serving WHERE customer_id = ?", [customer_id]
    ).fetchdf()
    rows = df.to_dict(orient="records") if df is not None else []
    if not rows:
        raise KeyError(customer_id)
    r = rows[0]
    top_categories = []
    for col, label in (
        ("top_product_group", "product group"),
        ("top_product_type", "product type"),
        ("top_colour_group", "colour group"),
        ("top_index_name", "index"),
        ("top_department", "department"),
    ):
        v = r.get(col)
        if v is None or v != v:  # None or NaN (cold-start members have no affinity)
            continue
        top_categories.append(CategoryAffinity(feature=label, code=int(v), label=f"{label} #{int(v)}"))
    return CustomerProfileResponse(
        customer=row_to_summary(r),
        first_purchase_date=str(r["first_purchase_date"]) if r.get("first_purchase_date") else None,
        last_purchase_date=str(r["last_purchase_date"]) if r.get("last_purchase_date") else None,
        top_categories=top_categories,
    )


def get_history(customer_id: str, limit: int) -> HistoryResponse:
    require(customers=True)
    rows = query_history(customer_id, limit)
    from ..schemas import Article

    articles = get_articles_by_ids([r["article_id"] for r in rows])
    items = []
    for r in rows:
        d = articles.get(r["article_id"])
        items.append(
            {
                "article_id": format_article_id(r["article_id"]),
                "t_dat": r["t_dat"],
                "price": r["price"],
                "sales_channel_id": r["sales_channel_id"],
                "article": Article(**d) if d else None,
            }
        )
    con = connection()
    total_row = con.execute(
        "SELECT purchase_count FROM customers_serving WHERE customer_id = ?", [customer_id]
    ).fetchone()
    range_start = min((r["t_dat"] for r in rows), default=None)
    range_end = max((r["t_dat"] for r in rows), default=None)
    return HistoryResponse(
        customer_id=customer_id,
        items=[HistoryItem(**i) for i in items],
        total_transactions=int(total_row[0]) if total_row and total_row[0] is not None else len(items),
        returned=len(items),
        range_start=range_start,
        range_end=range_end,
    )
