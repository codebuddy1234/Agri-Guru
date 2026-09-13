"""Shared FastAPI dependencies: database session, current user, role guards."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.database.models.enums import UserRole
from app.database.models.user import User
from app.database.session import get_session
from app.ml.crop_recommendation.inference.predictor import (
    CropRecommendationPredictor,
    get_predictor,
)

# auto_error=False so a missing header raises our UnauthorizedError (and the
# standard envelope) rather than FastAPI's bare {"detail": ...} shape.
_bearer = HTTPBearer(auto_error=False)


def db_session() -> Generator[Session, None, None]:
    yield from get_session()


DbSession = Annotated[Session, Depends(db_session)]


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: DbSession,
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Sign in to continue.")

    payload = decode_token(credentials.credentials, expected_type="access")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise UnauthorizedError("Invalid authentication token.") from None

    user = session.get(User, user_id)
    if not user:
        # Token is validly signed but the account is gone.
        raise UnauthorizedError("Invalid authentication token.")
    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_role(*allowed: UserRole):
    """Role guard. Expert and admin routes in later phases reuse this
    unchanged - that is the point of building it now."""

    def _guard(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise ForbiddenError()
        return user

    return _guard


CurrentFarmer = Annotated[User, Depends(require_role(UserRole.FARMER))]


def predictor() -> CropRecommendationPredictor:
    return get_predictor()


Predictor = Annotated[CropRecommendationPredictor, Depends(predictor)]
