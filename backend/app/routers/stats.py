"""Dataset/model statistics endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..core.config import get_settings
from ..core.serving import serving_status
from ..core.store import read_meta
from ..schemas import StatsResponse

router = APIRouter(tags=["stats"])


@router.get("/api/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    s = get_settings()
    meta = read_meta()
    if not meta:
        raise HTTPException(
            status_code=503,
            detail="pipeline metadata not found — run the offline build scripts first",
        )
    status = serving_status(s)
    return StatsResponse(
        status="ok" if status["customers_serving"] and status["recommendation_buckets"] else "partial",
        dataset=meta.get("dataset", {}),
        serving={
            **status,
            "serving_data_mb": _dir_size_mb(s.serving_data_dir),
            "recommendations_mb": _dir_size_mb(s.recommendations_dir),
            "models_mb": _dir_size_mb(s.models_dir),
        },
        model={
            "algorithm": "hybrid item-item collaborative + content + popularity + repeat-purchase",
            "weights": (meta.get("recommendations") or {}).get("weights", {}),
            "candidate_limit": (meta.get("recommendations") or {}).get("candidate_limit"),
            "neighbor_limit": (meta.get("recommendations") or {}).get("neighbor_limit"),
            "half_life_days": (meta.get("neighbors") or {}).get("half_life_days"),
            "built_at": (meta.get("recommendations") or {}).get("built_at"),
        },
    )


def _dir_size_mb(path) -> float:
    import pathlib

    d = pathlib.Path(path)
    if not d.exists():
        return 0.0
    return round(sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / 1e6, 1)
