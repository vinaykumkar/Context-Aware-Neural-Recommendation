"""Customer endpoints: discovery, profile, history, recommendations."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query

from ..core.config import get_settings
from ..core.store import StoreNotReady, connection
from ..schemas import CustomerListResponse, CustomerProfileResponse, HistoryResponse, RecommendationResponse
from ..services import customers as customer_service
from ..services.recommendations import CustomerNotFound, get_recommendations

router = APIRouter(prefix="/api/customers", tags=["customers"])

CUSTOMER_ID_RE = re.compile(r"^[0-9a-f]{64}$")


def valid_customer_id(customer_id: str) -> str:
    if not CUSTOMER_ID_RE.match(customer_id):
        raise HTTPException(status_code=422, detail="customer_id must be a 64-character hex string")
    return customer_id


def db():
    return connection()


@router.get("", response_model=CustomerListResponse)
def list_customers(
    q: str | None = Query(None, max_length=64, description="substring search on customer id"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    has_purchases: bool | None = Query(None),
    sort: str = Query("purchase_count", pattern="^(purchase_count|total_spent|recency|customer_id)$"),
    age_min: int | None = Query(None, ge=10, le=120),
    age_max: int | None = Query(None, ge=10, le=120),
    con=Depends(db),
) -> CustomerListResponse:
    try:
        return customer_service.search_customers(
            con, q, page, page_size, has_purchases, sort, age_min, age_max
        )
    except StoreNotReady as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/{customer_id}", response_model=CustomerProfileResponse)
def customer_profile(customer_id: str) -> CustomerProfileResponse:
    valid_customer_id(customer_id)
    try:
        return customer_service.get_customer_profile(customer_id)
    except StoreNotReady as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except KeyError:
        raise HTTPException(status_code=404, detail="customer not found") from None


@router.get("/{customer_id}/history", response_model=HistoryResponse)
def customer_history(
    customer_id: str,
    limit: int = Query(60, ge=1, le=200),
) -> HistoryResponse:
    valid_customer_id(customer_id)
    s = get_settings()
    try:
        return customer_service.get_history(customer_id, min(limit, s.history_per_customer))
    except StoreNotReady as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/{customer_id}/recommendations", response_model=RecommendationResponse)
def customer_recommendations(
    customer_id: str,
    count: int = Query(10, ge=1, le=50),
    exclude_purchased: bool | None = Query(None),
    diversify: bool | None = Query(None),
) -> RecommendationResponse:
    valid_customer_id(customer_id)
    s = get_settings()
    try:
        return get_recommendations(
            customer_id,
            count=count,
            exclude_purchased=s.exclude_purchased if exclude_purchased is None else exclude_purchased,
            diversify=s.diversity_rerank if diversify is None else diversify,
        )
    except CustomerNotFound:
        raise HTTPException(
            status_code=404,
            detail="no recommendation pool for this customer",
        ) from None
    except StoreNotReady as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
