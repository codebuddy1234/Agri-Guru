"""Test fixtures.

Tests run against a real PostgreSQL database, not SQLite. The schema uses
JSONB, UUID defaults and PostgreSQL enums, so a SQLite substitute would test
a different schema than the one that ships - exactly the kind of gap that
lets a migration bug reach production.

Set TEST_DATABASE_URL to point at a scratch database. It is created fresh and
dropped between runs.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator

import pytest

# Configure the environment before any application module is imported, since
# Settings is read at import time.
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-for-pytest-not-a-real-one-0123456789")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://agriguru:agriguru@localhost:5432/agriguru_test",
    ),
)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.main import create_app  # noqa: E402

import app.database.models  # noqa: E402,F401


@pytest.fixture(scope="session")
def engine():
    settings = get_settings()
    eng = create_engine(settings.sqlalchemy_url)
    # Build the schema from the models. Migrations are exercised separately by
    # running `alembic upgrade head` in CI.
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db(engine) -> Generator[Session, None, None]:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture(scope="session")
def client(engine) -> Generator[TestClient, None, None]:
    """TestClient with lifespan run, so the model is actually loaded."""
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def clean_db(engine) -> Generator[None, None, None]:
    """Truncate between tests so each one starts from a known state."""
    yield
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE crop_predictions, farms, farmer_profiles, users "
                "RESTART IDENTITY CASCADE"
            )
        )


def unique_email() -> str:
    return f"farmer_{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture
def farmer(client) -> dict:
    """A registered farmer with a valid access token."""
    email = unique_email()
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Shetkari123",
            "full_name": "Test Farmer",
            "preferred_language": "mr",
            "district": "Nashik",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()["data"]
    return {
        "email": email,
        "password": "Shetkari123",
        "user_id": body["user"]["id"],
        "token": body["tokens"]["access_token"],
        "refresh": body["tokens"]["refresh_token"],
        "headers": {"Authorization": f"Bearer {body['tokens']['access_token']}"},
    }


VALID_PREDICTION_INPUT = {
    "nitrogen": 90,
    "phosphorus": 42,
    "potassium": 43,
    "temperature": 20.9,
    "humidity": 82.0,
    "ph": 6.5,
    "rainfall": 202.9,
}
