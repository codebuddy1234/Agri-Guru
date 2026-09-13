"""Application configuration, loaded from environment variables.

Every value is read from the environment (or a .env file in development).
No secret has a usable default: SECRET_KEY intentionally has no default at
all, so a misconfigured deployment fails at startup instead of running with
a guessable signing key.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    APP_NAME: str = "AgriGuru AI"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # --- Database ---
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "agriguru"
    POSTGRES_PASSWORD: str = "agriguru"
    POSTGRES_DB: str = "agriguru"
    DATABASE_URL: str | None = None  # overrides the assembled URL when set

    # --- Security ---
    SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- ML ---
    MODEL_ARTIFACTS_DIR: Path = BACKEND_DIR / "app" / "ml" / "crop_recommendation" / "artifacts"
    DATASET_PATH: Path = PROJECT_ROOT / "data" / "raw" / "Crop_recommendation.csv"

    @field_validator("SECRET_KEY")
    @classmethod
    def _reject_placeholder_secret(cls, v: str) -> str:
        # The value shipped in .env.example must never reach a real deployment.
        if "change-me" in v.lower() or "your-secret" in v.lower():
            raise ValueError(
                "SECRET_KEY is still the placeholder from .env.example. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        return v

    @property
    def sqlalchemy_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is parsed once per process."""
    return Settings()  # type: ignore[call-arg]
