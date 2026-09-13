"""Password hashing and JWT handling.

Access tokens are short-lived; refresh tokens are long-lived and carry a
distinct `type` claim. Checking that claim is what stops a refresh token
from being replayed as an access token (a common and quiet vulnerability
in hand-rolled JWT setups).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

TokenType = Literal["access", "refresh"]

BCRYPT_MAX_BYTES = 72


def hash_password(plain: str) -> str:
    # bcrypt silently truncates beyond 72 bytes; reject rather than let a
    # long passphrase be quietly shortened into a weaker one.
    encoded = plain.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes.")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    encoded = plain.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed hash in the database -> a failed login, not a 500.
        return False


def _create_token(subject: str, role: str, token_type: TokenType, expires_in: timedelta) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires_in,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, role: str) -> str:
    settings = get_settings()
    return _create_token(
        subject, role, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(subject: str, role: str) -> str:
    settings = get_settings()
    return _create_token(
        subject, role, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Your session has expired. Please sign in again.") from None
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid authentication token.") from None

    if payload.get("type") != expected_type:
        raise UnauthorizedError("Invalid authentication token.")
    if not payload.get("sub"):
        raise UnauthorizedError("Invalid authentication token.")
    return payload
