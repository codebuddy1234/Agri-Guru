"""Authentication request/response schemas."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.database.models.enums import Language, UserRole

# Indian mobile numbers: 10 digits starting 6-9, optional +91 / 0 prefix.
MOBILE_PATTERN = re.compile(r"^(?:\+91[\-\s]?|0)?[6-9]\d{9}$")


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=120)
    mobile: str | None = Field(default=None, max_length=20)
    preferred_language: Language = Language.MARATHI
    district: str | None = Field(default=None, max_length=80)
    taluka: str | None = Field(default=None, max_length=80)
    village: str | None = Field(default=None, max_length=120)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        # Deliberately modest: a farmer on a feature phone keyboard is the
        # user. Length plus a digit beats a rule set that drives people to
        # write the password down.
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number.")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter.")
        return v

    @field_validator("mobile")
    @classmethod
    def _valid_mobile(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        compact = v.replace(" ", "").replace("-", "")
        if not MOBILE_PATTERN.match(compact):
            raise ValueError("Enter a valid 10-digit Indian mobile number.")
        return compact[-10:]


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until the access token expires


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    mobile: str | None
    role: UserRole
    is_active: bool
    created_at: datetime


class AuthenticatedUser(BaseModel):
    """Returned by /auth/me and by register/login alongside the tokens."""

    user: UserOut
    full_name: str | None = None
    preferred_language: Language | None = None
    has_profile: bool = False
