"""Central configuration for the H&M recommendation system.

All paths are resolved relative to the project root unless absolute, so the
repository stays portable. Values come from environment variables (optionally
loaded from a local ``.env`` file) with sensible development defaults.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _load_dotenv() -> None:
    """Minimal .env loader (no third-party dependency needed)."""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


def _resolve(path_value: str) -> Path:
    p = Path(path_value)
    return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()


@dataclass(frozen=True)
class Settings:
    # Data locations
    data_dir: Path = field(default_factory=lambda: _resolve(os.getenv("DATA_DIR", "./parquet")))
    serving_data_dir: Path = field(default_factory=lambda: _resolve(os.getenv("SERVING_DATA_DIR", "./serving_data")))
    recommendations_dir: Path = field(default_factory=lambda: _resolve(os.getenv("RECOMMENDATIONS_DIR", "./recommendations")))
    models_dir: Path = field(default_factory=lambda: _resolve(os.getenv("MODELS_DIR", "./models")))

    # Images: local dir takes precedence, then URL template, then placeholders.
    image_dir: Path | None = field(default_factory=lambda: _resolve(os.getenv("IMAGE_DIR", "")) if os.getenv("IMAGE_DIR") else None)
    image_url_template: str | None = field(default_factory=lambda: os.getenv("IMAGE_URL_TEMPLATE") or None)

    # Server
    host: str = os.getenv("BACKEND_HOST", "127.0.0.1")
    port: int = int(os.getenv("BACKEND_PORT", "8000"))
    cors_origins: list[str] = field(default_factory=lambda: [
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()
    ])

    # Serving layout (must match the offline pipeline)
    num_buckets: int = int(os.getenv("NUM_BUCKETS", "32"))
    history_per_customer: int = int(os.getenv("HISTORY_PER_CUSTOMER", "60"))
    default_recommendation_count: int = int(os.getenv("DEFAULT_RECOMMENDATION_COUNT", "10"))
    max_recommendation_count: int = int(os.getenv("MAX_RECOMMENDATION_COUNT", "50"))
    default_page_size: int = int(os.getenv("DEFAULT_PAGE_SIZE", "24"))
    max_page_size: int = int(os.getenv("MAX_PAGE_SIZE", "100"))

    # Feature toggles
    exclude_purchased: bool = os.getenv("RECS_EXCLUDE_PURCHASED", "true").lower() == "true"
    diversity_rerank: bool = os.getenv("RECS_DIVERSITY_RERANK", "true").lower() == "true"
    max_per_product_group: int = int(os.getenv("RECS_MAX_PER_GROUP", "4"))

    @property
    def history_dir(self) -> Path:
        return self.serving_data_dir / "history"

    @property
    def recs_dir(self) -> Path:
        return self.recommendations_dir / "buckets"

    def ensure_dirs(self) -> None:
        for d in (self.serving_data_dir, self.recommendations_dir, self.models_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
