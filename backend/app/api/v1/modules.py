"""Module registry.

The dashboard renders from this list rather than from hardcoded markup, so
activating a future module is a status change here instead of a frontend
rewrite - and a "coming soon" card can never accidentally become a working
link to a feature that does not exist.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.api.v1.deps import CurrentUser
from app.schemas.common import envelope

router = APIRouter(tags=["modules"])

#: status is "available" or "coming_soon". Nothing else is rendered as usable.
MODULES: list[dict[str, Any]] = [
    {
        "key": "crop_recommendation",
        "icon": "sprout",
        "status": "available",
        "route": "/crop-recommendation",
        "phase": 1,
    },
    {"key": "disease_detection", "icon": "leaf", "status": "coming_soon", "route": None, "phase": 2},
    {"key": "weather", "icon": "cloud-sun", "status": "coming_soon", "route": None, "phase": 2},
    {"key": "market_prices", "icon": "trending-up", "status": "coming_soon", "route": None, "phase": 3},
    {"key": "fertilizer", "icon": "flask-conical", "status": "coming_soon", "route": None, "phase": 3},
    {"key": "yield_prediction", "icon": "bar-chart-3", "status": "coming_soon", "route": None, "phase": 4},
    {"key": "schemes", "icon": "landmark", "status": "coming_soon", "route": None, "phase": 4},
    {"key": "expert_review", "icon": "user-check", "status": "coming_soon", "route": None, "phase": 4},
]


@router.get("/modules", summary="Which platform modules are active")
def list_modules(user: CurrentUser) -> dict[str, Any]:
    # Titles and descriptions are not returned: the frontend resolves each
    # key against its locale files, so this endpoint stays language-neutral.
    return envelope(MODULES)
