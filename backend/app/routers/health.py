"""Health and app configuration endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from ..core.config import get_settings
from ..core.serving import serving_status
from ..schemas import AppConfigResponse, HealthResponse
from ..services.images import image_mode

router = APIRouter()

VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse)
@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    s = get_settings()
    status = serving_status(s)
    ready = status["customers_serving"] and status["articles_serving"]
    message = None
    if not ready:
        message = "Serving data not built yet — run `python scripts/build_serving_data.py`."
    elif status["recommendation_buckets"] == 0:
        message = "Recommendations not generated yet — run `python scripts/build_recommendations.py`."
    return HealthResponse(
        status="ok" if ready else "degraded",
        version=VERSION,
        serving=status,
        message=message,
    )


@router.get("/api/config", response_model=AppConfigResponse)
def app_config() -> AppConfigResponse:
    s = get_settings()
    return AppConfigResponse(
        image_mode=image_mode(),
        image_url_template=bool(s.image_url_template),
        history_per_customer=s.history_per_customer,
        max_recommendation_count=s.max_recommendation_count,
        diversity_rerank=s.diversity_rerank,
        exclude_purchased=s.exclude_purchased,
    )
