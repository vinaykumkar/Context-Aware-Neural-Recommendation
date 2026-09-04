"""Recommendation serving: precomputed buckets + light runtime reranking."""
from __future__ import annotations

from pathlib import Path

from ..core.article_id import format_article_id, parse_article_id
from ..core.config import get_settings
from ..core.serving import customer_bucket
from ..core.store import connection, query_recommendations, recs_bucket_path, require
from ..schemas import Article, ArticleFeature, ArticleStats, ComponentScores, RecommendationItem, RecommendationResponse
from ..services.articles import get_articles_by_ids
from ..services.images import resolve_article_image

REASON_TEXT = {
    "COLLABORATIVE": "Customers with similar taste repeatedly bought this",
    "CONTENT_SIMILARITY": "Matches this customer's preferred styles and attributes",
    "POPULARITY": "A strong seller across H&M shoppers",
    "REPEAT_PURCHASE": "Based on items this customer re-buys",
    "HYBRID": "Blended match across several behavior signals",
}


class CustomerNotFound(Exception):
    pass


def popularity_fallback(limit: int) -> list[dict]:
    con = connection()
    require(articles=True)
    rows = con.execute(
        """
        SELECT p.article_id, p.popularity_rank
        FROM article_popularity p
        JOIN articles_serving a USING (article_id)
        WHERE COALESCE(a.purchase_count, 0) > 0
        ORDER BY p.popularity_rank
        LIMIT ?
        """,
        [limit],
    ).fetchall()
    return [
        {
            "article_id": r[0],
            "rank": i + 1,
            "score": None,
            "comp_collaborative": 0.0,
            "comp_content": 0.0,
            "comp_popularity": 1.0,
            "comp_repurchase": 0.0,
            "reason": "POPULARITY",
        }
        for i, r in enumerate(rows)
    ]


def purchased_set(customer_id: str) -> set[int]:
    """Distinct articles the customer bought (one small bucket file)."""
    s = get_settings()
    bucket = customer_bucket(customer_id, s.num_buckets)
    path = Path(s.history_dir) / f"bucket_{bucket:02d}.parquet"
    if not path.exists():
        return set()
    con = connection()
    rows = con.execute(
        f"SELECT DISTINCT article_id FROM read_parquet('{path.as_posix()}') WHERE customer_id = ?",
        [customer_id],
    ).fetchall()
    return {r[0] for r in rows}


def diversity_filter(items: list[RecommendationItem], max_per_group: int) -> list[RecommendationItem]:
    """Greedy cap on candidates sharing one product group (encoded index)."""
    if max_per_group <= 0 or not items:
        return items
    con = connection()
    require(articles=True)
    internal = {i.article_id: parse_article_id(i.article_id) for i in items}
    ids = ",".join(str(v) for v in internal.values())
    groups = dict(
        con.execute(
            f"SELECT article_id, product_group_name_index FROM articles_serving WHERE article_id IN ({ids})"
        ).fetchall()
    )
    kept: list[RecommendationItem] = []
    counts: dict[int, int] = {}
    for item in items:
        g = groups.get(internal[item.article_id])
        if g is not None and counts.get(g, 0) >= max_per_group:
            continue
        if g is not None:
            counts[g] = counts.get(g, 0) + 1
        kept.append(item)
    return kept


def _minimal_article(article_id: int | str) -> Article:
    """Fallback when an article has no serving row (keeps API shape stable)."""
    return Article(
        article_id=format_article_id(article_id),
        features=[],
        label=None,
        product_type=None,
        product_group=None,
        colour=None,
        department=None,
        section=None,
        garment_group=None,
        graphical_appearance=None,
        index_group=None,
        index_name=None,
        stats=ArticleStats(
            purchase_count=0,
            unique_customers=0,
            avg_price=None,
            first_sale_date=None,
            last_sale_date=None,
            sales_last_28d=0,
            sales_last_84d=0,
            popularity_rank=None,
        ),
        image_url=resolve_article_image(article_id),
    )


def get_recommendations(
    customer_id: str,
    count: int,
    exclude_purchased: bool,
    diversify: bool,
) -> RecommendationResponse:
    s = get_settings()
    require(customers=True)
    known = connection().execute(
        "SELECT 1 FROM customers_serving WHERE customer_id = ?", [customer_id]
    ).fetchone()
    if not known:
        raise CustomerNotFound(customer_id)

    bucket_path = recs_bucket_path(customer_id)
    rows = query_recommendations(customer_id, s.max_recommendation_count) if Path(bucket_path).exists() else []
    source = "precomputed"
    if not rows:
        rows = popularity_fallback(s.default_recommendation_count)
        source = "popularity_fallback"

    bought = purchased_set(customer_id) if exclude_purchased else set()

    items: list[RecommendationItem] = []
    filtered = 0
    for r in rows:
        if exclude_purchased and r["article_id"] in bought:
            filtered += 1
            continue
        reason = r["reason"] if r["reason"] in REASON_TEXT else "HYBRID"
        items.append(
            RecommendationItem(
                rank=len(items) + 1,
                article_id=format_article_id(r["article_id"]),
                score=float(r["score"]) if r["score"] is not None else 0.0,
                components=ComponentScores(
                    collaborative=float(r["comp_collaborative"] or 0),
                    content=float(r["comp_content"] or 0),
                    popularity=float(r["comp_popularity"] or 0),
                    repurchase=float(r["comp_repurchase"] or 0),
                ),
                reason=reason,  # type: ignore[arg-type]
                reason_text=REASON_TEXT[reason],
            )
        )

    if diversify:
        items = diversity_filter(items, s.max_per_product_group)
    items = items[:count]

    raw = get_articles_by_ids([parse_article_id(i.article_id) for i in items])
    for i in items:
        internal = parse_article_id(i.article_id)
        d = raw.get(internal)
        i.article = Article(**d) if d else _minimal_article(i.article_id)
    for pos, i in enumerate(items, start=1):
        i.rank = pos

    return RecommendationResponse(
        customer_id=customer_id,
        items=items,
        source=source,  # type: ignore[arg-type]
        filtered_out=filtered,
        count=len(items),
    )
