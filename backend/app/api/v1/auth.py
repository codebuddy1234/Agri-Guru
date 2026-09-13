"""Authentication routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from app.api.v1.deps import CurrentUser, DbSession
from app.schemas.auth import (
    AuthenticatedUser,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    UserOut,
)
from app.schemas.common import envelope
from app.services.auth_service import AuthService
from app.services.farmer_service import FarmerService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Register a farmer")
def register(payload: RegisterRequest, session: DbSession) -> dict[str, Any]:
    user, profile, tokens = AuthService(session).register_farmer(payload)
    return envelope(
        {
            "user": UserOut.model_validate(user).model_dump(mode="json"),
            "profile": {
                "full_name": profile.full_name,
                "preferred_language": profile.preferred_language.value,
            },
            "tokens": tokens.model_dump(),
        }
    )


@router.post("/login", summary="Sign in")
def login(payload: LoginRequest, session: DbSession) -> dict[str, Any]:
    user, tokens = AuthService(session).login(payload.email, payload.password)
    profile = user.farmer_profile
    return envelope(
        {
            "user": UserOut.model_validate(user).model_dump(mode="json"),
            "profile": (
                {
                    "full_name": profile.full_name,
                    "preferred_language": profile.preferred_language.value,
                }
                if profile
                else None
            ),
            "tokens": tokens.model_dump(),
        }
    )


@router.post("/refresh", summary="Exchange a refresh token for a new access token")
def refresh(payload: RefreshRequest, session: DbSession) -> dict[str, Any]:
    tokens = AuthService(session).refresh(payload.refresh_token)
    return envelope({"tokens": tokens.model_dump()})


@router.get("/me", summary="Current signed-in user")
def me(user: CurrentUser, session: DbSession) -> dict[str, Any]:
    profile = None
    try:
        profile = FarmerService(session).get_profile(user.id)
    except Exception:  # noqa: BLE001 - experts/admins have no farmer profile
        profile = None

    return envelope(
        AuthenticatedUser(
            user=UserOut.model_validate(user),
            full_name=profile.full_name if profile else None,
            preferred_language=profile.preferred_language if profile else None,
            has_profile=profile is not None,
        ).model_dump(mode="json")
    )
