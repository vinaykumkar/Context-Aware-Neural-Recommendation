"""Article endpoints: details + similar articles from the neighbor models."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from ..core.config import get_settings
from ..core.article_id import format_article_id, parse_article_id
from ..core.store import StoreNotReady, connection, require
from ..schemas import Article, ArticleListResponse, ArticleResponse, SimilarArticle
from ..services.articles import article_exists, article_row_to_dict, get_articles_by_ids, search_articles

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("", response_model=ArticleListResponse)
def list_articles(
    q: str | None = Query(None, description="Search keyword in article description, type, category, colour"),
    gender: str | None = Query(None, description="Filter by gender/department (Ladieswear, Menswear, Divided, etc.)"),
    product_group: str | None = Query(None, description="Filter by product group (Garment Upper body, etc.)"),
    age_group: str | None = Query(None, description="Filter by demographic age group (18-25, 26-35, 36-50, 51-100)"),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    sort: str = Query("popularity", pattern="^(popularity|price_asc|price_desc|purchase_count|recency)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
) -> ArticleListResponse:
    """Catalog search and filter endpoint."""
    try:
        require(articles=True)
    except StoreNotReady as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    con = connection()
    result = search_articles(
        con=con,
        q=q,
        gender=gender,
        product_group=product_group,
        age_group=age_group,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return ArticleListResponse(**result)


@router.get("/popular", response_model=list[Article])
def popular_articles(limit: int = Query(12, ge=1, le=48)) -> list[Article]:
    """Globally popular articles (used for the landing rail + fallbacks)."""
    try:
        require(articles=True)
    except StoreNotReady as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    con = connection()
    rows = con.execute(
        f"""
        SELECT a.*, p.popularity_rank,
               d.product_type_name, d.product_group_name, d.colour_group_name,
               d.department_name, d.section_name, d.garment_group_name,
               d.graphical_appearance_name, d.index_group_name, d.index_name
        FROM articles_serving a
        JOIN article_popularity p USING (article_id)
        LEFT JOIN articles_display d USING (article_id)
        WHERE COALESCE(a.purchase_count, 0) > 0
        ORDER BY p.popularity_rank
        LIMIT {int(limit)}
        """
    ).fetchdf().to_dict(orient="records")
    return [Article(**article_row_to_dict(r)) for r in rows]


@router.get("/{article_id}", response_model=ArticleResponse)
def article_detail(
    article_id: str,
    similar_count: int = Query(8, ge=0, le=20),
) -> ArticleResponse:
    """Accepts the canonical 10-digit form ("0800691008") or bare numeric ("800691008")."""
    internal = parse_article_id(article_id)
    if internal is None:
        raise HTTPException(status_code=422, detail="article_id must be a positive numeric id (9-10 digits)")
    try:
        require(articles=True)
    except StoreNotReady as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    if not article_exists(internal):
        raise HTTPException(status_code=404, detail="article not found")

    con = connection()
    row = con.execute(
        f"""
        SELECT a.*, p.popularity_rank,
               d.product_type_name, d.product_group_name, d.colour_group_name,
               d.department_name, d.section_name, d.garment_group_name,
               d.graphical_appearance_name, d.index_group_name, d.index_name
        FROM articles_serving a
        LEFT JOIN article_popularity p USING (article_id)
        LEFT JOIN articles_display d USING (article_id)
        WHERE a.article_id = {internal}
        """
    ).fetchdf().to_dict(orient="records")[0]
    article = article_row_to_dict(row)

    similar: list[SimilarArticle] = []
    if similar_count > 0:
        nb_path = get_settings().models_dir / "item_neighbors_collab.parquet"
        if nb_path.exists():
            nbr_rows = con.execute(
                f"""
                SELECT neighbor_id, score FROM read_parquet('{nb_path.as_posix()}')
                WHERE item_id = {internal}
                ORDER BY sim_rank LIMIT {int(similar_count)}
                """
            ).fetchdf().to_dict(orient="records")
            if nbr_rows:
                articles = get_articles_by_ids([int(r["neighbor_id"]) for r in nbr_rows])
                similar = [
                    SimilarArticle(
                        article_id=format_article_id(r["neighbor_id"]),
                        score=float(r["score"]),
                        article=articles.get(int(r["neighbor_id"])),
                    )
                    for r in nbr_rows
                ]
    return ArticleResponse(article=article, similar=similar)
