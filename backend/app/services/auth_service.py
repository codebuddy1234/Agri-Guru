"""Authentication business logic.

Routes stay thin: they validate a schema and call one of these methods. All
transaction handling lives here.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, InvalidCredentialsError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database.models.enums import UserRole
from app.database.models.farmer_profile import FarmerProfile
from app.database.models.user import User
from app.schemas.auth import RegisterRequest, TokenPair

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- helpers ---

    def _get_user_by_email(self, email: str) -> User | None:
        # Emails are compared case-insensitively: "Ramesh@x.com" and
        # "ramesh@x.com" must not become two accounts.
        stmt = select(User).where(func.lower(User.email) == email.lower())
        return self.session.scalar(stmt)

    def _issue_tokens(self, user: User) -> TokenPair:
        settings = get_settings()
        return TokenPair(
            access_token=create_access_token(str(user.id), user.role.value),
            refresh_token=create_refresh_token(str(user.id), user.role.value),
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # --- operations ---

    def register_farmer(self, payload: RegisterRequest) -> tuple[User, FarmerProfile, TokenPair]:
        """Create the user and their farmer profile in one transaction.

        A user row without a profile row would leave an account that can log
        in but has nothing to attach predictions to, so the two are created
        together or not at all.
        """
        if self._get_user_by_email(payload.email):
            raise ConflictError("An account with this email already exists.")

        user = User(
            email=payload.email.lower(),
            mobile=payload.mobile,
            password_hash=hash_password(payload.password),
            role=UserRole.FARMER,
            is_active=True,
        )
        profile = FarmerProfile(
            user=user,
            full_name=payload.full_name,
            preferred_language=payload.preferred_language,
            district=payload.district,
            taluka=payload.taluka,
            village=payload.village,
        )
        self.session.add(user)
        self.session.add(profile)

        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            # Lost the race against a concurrent registration, or the mobile
            # number is already taken.
            raise ConflictError("An account with this email or mobile already exists.") from None

        self.session.refresh(user)
        self.session.refresh(profile)
        logger.info("Registered farmer %s", user.id)
        return user, profile, self._issue_tokens(user)

    def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        user = self._get_user_by_email(email)

        # Always run a hash comparison, even when the user does not exist, so
        # response time does not reveal which emails are registered.
        stored_hash = user.password_hash if user else "$2b$12$" + "x" * 53
        password_ok = verify_password(password, stored_hash)

        if not user or not password_ok:
            raise InvalidCredentialsError()
        if not user.is_active:
            raise UnauthorizedError("This account has been deactivated.")

        user.last_login_at = datetime.now(UTC)
        self.session.commit()
        return user, self._issue_tokens(user)

    def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = self.session.get(User, payload["sub"])
        if not user or not user.is_active:
            raise UnauthorizedError("This account is no longer active.")
        return self._issue_tokens(user)
