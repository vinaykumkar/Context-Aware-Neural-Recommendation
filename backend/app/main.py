"""FastAPI application factory for the H&M recommendation system."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .core.config import get_settings
from .core.serving import serving_status
from .core.store import StoreNotReady
from .routers import articles, customers, health, stats
from .services.images import find_image_file
from .services.recommendations import CustomerNotFound

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("hm-recommender")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="H&M Personalized Recommendation API",
        description="Serves precomputed hybrid recommendations for the H&M dataset. "
        "Heavy computation happens offline; request-time work is O(bucket lookup).",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    app.include_router(health.router)
    app.include_router(customers.router)
    app.include_router(articles.router)
    app.include_router(stats.router)

    @app.exception_handler(StoreNotReady)
    async def store_not_ready_handler(request: Request, exc: StoreNotReady):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(CustomerNotFound)
    async def customer_not_found_handler(request: Request, exc: CustomerNotFound):
        return JSONResponse(status_code=404, content={"detail": "no recommendation pool for this customer"})

    @app.get("/api/images/{article_id}", include_in_schema=False)
    @app.get("/images/{article_id}", include_in_schema=False)
    async def article_image(article_id: str):
        """Serve a product image for the canonical 10-digit article id.

        Accepts "0800691008" (or bare numeric). The id is validated strictly
        and the file must resolve through the image resolver (deterministic
        path or the prebuilt index) — no arbitrary filesystem access, no
        raw Windows paths are exposed.
        """
        from .core.article_id import parse_article_id

        if parse_article_id(article_id) is None:
            return JSONResponse(status_code=422, content={"detail": "invalid article id"})
        file = find_image_file(article_id)
        if file is None:
            return JSONResponse(status_code=404, content={"detail": "image not available"})
        return FileResponse(file, media_type=_media_type(file))

    @app.on_event("startup")
    async def startup() -> None:
        status = serving_status()
        logger.info("startup serving status: %s", status)
        if not status["customers_serving"]:
            logger.warning(
                "Serving data missing — run `python scripts/build_serving_data.py` "
                "then `python scripts/build_models.py` and `python scripts/build_recommendations.py`."
            )

    return app


def _media_type(file: Path) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(file.suffix.lower(), "application/octet-stream")


app = create_app()
