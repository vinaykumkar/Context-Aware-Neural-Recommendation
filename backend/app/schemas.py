"""Typed API response models."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ArticleFeature(BaseModel):
    feature: str
    code: int


class ArticleStats(BaseModel):
    purchase_count: int
    unique_customers: int
    avg_price: float | None
    first_sale_date: str | None
    last_sale_date: str | None
    sales_last_28d: int
    sales_last_84d: int
    popularity_rank: int | None


class Article(BaseModel):
    # canonical external form: 10-digit zero-padded string (e.g. "0800691008")
    article_id: str
    features: list[ArticleFeature]
    stats: ArticleStats
    image_url: str | None = None
    # human-readable display metadata (from articles_display) — None when absent
    label: str | None = None  # reserved: a product name column does not exist in the data
    product_type: str | None = None
    product_group: str | None = None
    colour: str | None = None
    department: str | None = None
    section: str | None = None
    garment_group: str | None = None
    graphical_appearance: str | None = None
    index_group: str | None = None
    index_name: str | None = None


class ArticleListResponse(BaseModel):
    items: list[Article]
    total: int
    page: int
    page_size: int
    pages: int


class HistoryItem(BaseModel):
    article_id: str
    t_dat: str
    price: float
    sales_channel_id: int
    article: Article | None = None


class HistoryResponse(BaseModel):
    customer_id: str
    items: list[HistoryItem]
    total_transactions: int
    returned: int
    range_start: str | None = None
    range_end: str | None = None


class ComponentScores(BaseModel):
    collaborative: float = Field(ge=0, le=1)
    content: float = Field(ge=0, le=1)
    popularity: float = Field(ge=0, le=1)
    repurchase: float = Field(ge=0, le=1)


ReasonCode = Literal[
    "COLLABORATIVE",
    "CONTENT_SIMILARITY",
    "POPULARITY",
    "REPEAT_PURCHASE",
    "HYBRID",
]


class RecommendationItem(BaseModel):
    rank: int
    article_id: str
    score: float
    components: ComponentScores
    reason: ReasonCode
    reason_text: str
    article: Article | None = None


class RecommendationResponse(BaseModel):
    customer_id: str
    items: list[RecommendationItem]
    source: Literal["precomputed", "popularity_fallback"]
    filtered_out: int = 0
    count: int


class CustomerSummary(BaseModel):
    customer_id: str
    short_id: str
    age: int | None
    club_member_status: str | None
    fashion_news_frequency: str | None
    active: float | None
    purchase_count: int
    unique_articles_count: int
    average_price: float | None
    total_spent: float | None
    recency_days: int | None
    purchase_frequency: float | None
    customer_lifetime_days: int | None
    has_purchases: bool


class CustomerListResponse(BaseModel):
    items: list[CustomerSummary]
    total: int
    page: int
    page_size: int
    pages: int


class CategoryAffinity(BaseModel):
    feature: str
    code: int
    label: str


class CustomerProfileResponse(BaseModel):
    customer: CustomerSummary
    first_purchase_date: str | None
    last_purchase_date: str | None
    top_categories: list[CategoryAffinity]


class SimilarArticle(BaseModel):
    article_id: str
    score: float
    article: Article | None = None


class ArticleResponse(BaseModel):
    article: Article
    similar: list[SimilarArticle]


class StatsResponse(BaseModel):
    status: str
    dataset: dict
    serving: dict
    model: dict


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    serving: dict
    message: str | None = None


class AppConfigResponse(BaseModel):
    image_mode: str
    image_url_template: bool
    history_per_customer: int
    max_recommendation_count: int
    diversity_rerank: bool
    exclude_purchased: bool
