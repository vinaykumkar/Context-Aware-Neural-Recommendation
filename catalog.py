"""Product catalog endpoints for the Discover & Shop experience.

All queries run against small serving parquet files via DuckDB —
articles_serving (stats) joined with articles_display (names) and
article_age_affinity (honest age-band popularity). The 31.8M-row
transaction table is never scanned at request time.

Category mapping is an explicit, inspectable translation of the dataset's
real ``product_group_name`` values — nothing is inferred from names that
do not exist in the data.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..core.store import StoreNotReady, connection, require
from ..schemas import CatalogFiltersResponse, CatalogProduct, CatalogResponse

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

# explicit mapping from real product_group_name values → display category
CATEGORY_BY_GROUP = {
    "Garment Upper body": "Upper Body",
    "Garment Lower body": "Lower Body",
    "Garment Full body": "Full Body",
    "Shoes": "Shoes & Footwear",
    "Accessories": "Accessories & Bags",
    "Bags": "Accessories & Bags",
    "Underwear": "Underwear, Socks & Nightwear",
    "Nightwear": "Underwear, Socks & Nightwear",
    "Underwear/nightwear": "Underwear, Socks & Nightwear",
    "Socks & Tights": "Underwear, Socks & Nightwear",
    "Swimwear": "Swimwear & Beachwear",
    "Unknown": "Other",
    "Cosmetic": "Other",
    "Items": "Other",
    "Furniture": "Other",
    "Garment and Shoe care": "Other",
    "Stationery": "Other",
    "Interior textile": "Other",
    "Fun": "Other",
}

SORTS = {
    "featured": "purchase_count DESC, a.article_id",
    "most_purchased": "purchase_count DESC",
    "least_purchased": "purchase_count ASC",
    "trending": "sales_last_28d DESC, purchase_count DESC",
    "name_asc": 'product_type_name ASC, "article_id"',
    "name_desc": 'product_type_name DESC, "article_id"',
    "article_id": "a.article_id ASC",
    "age_popular": "affinity_purchase_count DESC NULLS LAST, purchase_count DESC",
}

AGE_BANDS = ["under_18", "18_24", "25_34", "35_44", "45_54", "55_plus"]


def _catalog_base_query() -> str:
    return """
        FROM articles_serving a
        LEFT JOIN articles_display d USING (article_id)
    """


def _catalog_where(q: str | None, division: str | None, department: str | None,
                   colour: str | None, garment_group: str | None,
                   product_type: str | None, section: str | None,
                   category: str | None) -> tuple[str, list]:
    where = ["1=1"]
    params: list = []
    if q:
        fields = [
            "CAST(a.article_id AS VARCHAR)",
            "d.product_type_name", "d.product_group_name", "d.colour_group_name",
            "d.department_name", "d.garment_group_name", "d.section_name",
            "d.index_group_name",
        ]
        # AND across whitespace-separated terms, OR across fields per term:
        # "black dress" matches black items that are dresses
        for term in q.replace("%", "").replace("_", " ").split():
            like = f"%{term}%"
            marks = " OR ".join(f"{f} ILIKE ?" for f in fields)
            where.append(f"({marks})")
            params += [like] * len(fields)
    if division:
        where.append("d.index_group_name = ?")
        params.append(division)
    if department:
        where.append("d.index_name = ?")
        params.append(department)
    if colour:
        where.append("d.colour_group_name = ?")
        params.append(colour)
    if garment_group:
        where.append("d.garment_group_name = ?")
        params.append(garment_group)
    if product_type:
        where.append("d.product_type_name = ?")
        params.append(product_type)
    if section:
        where.append("d.section_name = ?")
        params.append(section)
    if category:
        groups = [g for g, c in CATEGORY_BY_GROUP.items() if c == category]
        if not groups:
            raise HTTPException(status_code=422, detail=f"unknown category: {category}")
        marks = ",".join("?" for _ in groups)
        where.append(f"d.product_group_name IN ({marks})")
        params += groups
    return " AND ".join(where), params


def _age_affinity_sql(age_band: str | None) -> str:
    if not age_band:
        return "SELECT 0 AS article_id, 0 AS affinity_purchase_count WHERE 1=0"
    path = (get_settings().serving_data_dir / "article_age_affinity.parquet").as_posix()
    return (
        f"SELECT article_id, purchase_count AS affinity_purchase_count "
        f"FROM read_parquet('{path}') WHERE age_band = '{age_band}'"
    )


from ..core.config import get_settings  # noqa: E402  (used in _age_affinity_sql)


@router.get("", response_model=CatalogResponse)
def catalog(
    q: str | None = Query(None, max_length=64),
    division: str | None = Query(None, max_length=48),
    department: str | None = Query(None, max_length=48),
    colour: str | None = Query(None, max_length=48),
    garment_group: str | None = Query(None, max_length=48),
    product_type: str | None = Query(None, max_length=48),
    section: str | None = Query(None, max_length=64),
    category: str | None = Query(None, max_length=48),
    age_band: str | None = Query(None, description="popular among age band"),
    sort: str = Query("featured", pattern="^(featured|most_purchased|least_purchased|trending|name_asc|name_desc|article_id|age_popular)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=60),
) -> CatalogResponse:
    try:
        require(articles=True)
    except StoreNotReady as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    if age_band and age_band not in AGE_BANDS:
        raise HTTPException(status_code=422, detail=f"unsupported age band — use one of {AGE_BANDS}")

    con = connection()
    where, params = _catalog_where(q, division, department, colour, garment_group, product_type, section, category)
    order = SORTS[sort]
    affinity = _age_affinity_sql(age_band if sort == "age_popular" else None)

    from_clause = f"""
        {_catalog_base_query()}
        LEFT JOIN ({affinity}) aff ON aff.article_id = a.article_id
        WHERE {where}
    """
    total = con.execute(f"SELECT COUNT(*) {from_clause}", params).fetchone()[0]
    offset = (page - 1) * page_size
    rows = con.execute(
        f"""
        SELECT a.article_id,
               d.product_type_name, d.product_group_name, d.colour_group_name,
               d.department_name, d.section_name, d.garment_group_name,
               d.index_group_name, d.index_name,
               a.purchase_count, a.sales_last_28d, a.sales_last_84d,
               COALESCE(aff.affinity_purchase_count, 0) AS affinity_purchase_count
        {from_clause}
        ORDER BY {order}
        LIMIT {page_size} OFFSET {offset}
        """,
        params,
    ).fetchdf().to_dict(orient="records")
    from ..services.images import resolve_article_image
    from ..core.article_id import format_article_id

    items = [
        CatalogProduct(
            article_id=format_article_id(r["article_id"]),
            product_type=r.get("product_type_name"),
            product_group=r.get("product_group_name"),
            colour=r.get("colour_group_name"),
            department=r.get("index_name"),
            section=r.get("section_name"),
            garment_group=r.get("garment_group_name"),
            division=r.get("index_group_name"),
            category=CATEGORY_BY_GROUP.get(r.get("product_group_name"), "Other"),
            purchase_count=int(r.get("purchase_count") or 0),
            sales_last_28d=int(r.get("sales_last_28d") or 0),
            image_url=resolve_article_image(r["article_id"]),
        )
        for r in rows
    ]
    pages = max(1, -(-total // page_size))
    return CatalogResponse(items=items, total=int(total), page=page, page_size=page_size, pages=pages)


@router.get("/filters", response_model=CatalogFiltersResponse)
def catalog_filters() -> CatalogFiltersResponse:
    """Distinct filter values with counts, derived from real article metadata."""
    try:
        require(articles=True)
    except StoreNotReady as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    con = connection()

    def distinct(col: str) -> list[dict]:
        rows = con.execute(
            f"SELECT d.{col} AS value, COUNT(*) AS count FROM articles_display d "
            "WHERE d." + col + " IS NOT NULL GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall()
        return [{"value": r[0], "count": int(r[1])} for r in rows]

    divisions = distinct("index_group_name")
    departments = distinct("index_name")
    colours = distinct("colour_group_name")
    garment_groups = distinct("garment_group_name")
    product_types = distinct("product_type_name")
    sections = distinct("section_name")

    group_counts = con.execute(
        "SELECT product_group_name, COUNT(*) FROM articles_display GROUP BY 1"
    ).fetchall()
    categories: dict[str, int] = {}
    for g, c in group_counts:
        if g is None:
            continue
        categories[CATEGORY_BY_GROUP.get(g, "Other")] = categories.get(CATEGORY_BY_GROUP.get(g, "Other"), 0) + c
    category_list = [{"value": k, "count": v} for k, v in sorted(categories.items(), key=lambda kv: -kv[1])]

    return CatalogFiltersResponse(
        divisions=divisions,
        departments=departments,
        colours=colours,
        garment_groups=garment_groups,
        product_types=product_types,
        sections=sections,
        categories=category_list,
        age_bands=AGE_BANDS,
    )
