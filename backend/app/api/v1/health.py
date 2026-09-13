"""Health endpoint.

Reports each dependency separately. The API is "degraded", not "down", when
the model is missing: authentication, profile and history all still work, and
saying otherwise would trigger the wrong operational response.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.database.session import database_is_reachable
from app.ml.crop_recommendation.inference.predictor import get_predictor
from app.schemas.common import envelope

router = APIRouter(tags=["health"])


@router.get("/health", summary="Service and dependency health")
def health(response: Response) -> dict[str, Any]:
    settings = get_settings()

    db_ok = database_is_reachable()
    try:
        model_health = get_predictor().health()
    except Exception:  # noqa: BLE001 - health must never raise
        model_health = {"status": "unavailable", "reason": "Predictor not initialised."}

    if not db_ok:
        overall = "down"          # nothing meaningful works without the database
    elif model_health["status"] != "available":
        overall = "degraded"      # predictions unavailable, everything else fine
    else:
        overall = "ok"

    if overall == "down":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return envelope(
        {
            "status": overall,
            "environment": settings.ENVIRONMENT,
            "checks": {
                "database": {"status": "available" if db_ok else "unavailable"},
                "crop_recommendation_model": model_health,
            },
        }
    )
