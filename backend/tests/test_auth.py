"""Registration, login, tokens and role handling."""

import pytest

from tests.conftest import unique_email


def test_register_creates_user_and_profile(client, clean_db):
    email = unique_email()
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Shetkari123",
            "full_name": "Ramesh Patil",
            "preferred_language": "mr",
        },
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["user"]["email"] == email
    assert data["user"]["role"] == "farmer"
    assert data["profile"]["full_name"] == "Ramesh Patil"
    assert data["tokens"]["access_token"]
    assert data["tokens"]["refresh_token"]


def test_register_rejects_duplicate_email(client, farmer):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": farmer["email"],
            "password": "Shetkari123",
            "full_name": "Impostor",
        },
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "CONFLICT"


def test_email_is_case_insensitive(client, clean_db):
    email = unique_email()
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Shetkari123", "full_name": "A B"},
    )
    # Same address, different case, must not become a second account.
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email.upper(), "password": "Shetkari123", "full_name": "C D"},
    )
    assert res.status_code == 409


@pytest.mark.parametrize(
    "password,reason",
    [
        ("short1", "too short"),
        ("allletters", "no digit"),
        ("12345678", "no letter"),
    ],
)
def test_register_rejects_weak_passwords(client, password, reason):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": unique_email(), "password": password, "full_name": "A B"},
    )
    assert res.status_code == 422, reason
    assert res.json()["error"]["code"] == "INVALID_INPUT"


def test_register_rejects_invalid_mobile(client):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email(),
            "password": "Shetkari123",
            "full_name": "A B",
            "mobile": "12345",
        },
    )
    assert res.status_code == 422


def test_login_succeeds_and_returns_language(client, farmer):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": farmer["email"], "password": farmer["password"]},
    )
    assert res.status_code == 200
    assert res.json()["data"]["profile"]["preferred_language"] == "mr"


def test_login_rejects_wrong_password(client, farmer):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": farmer["email"], "password": "WrongPassword1"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_error_does_not_reveal_whether_email_exists(client, farmer):
    """The same message for both cases, so login cannot enumerate accounts."""
    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email(), "password": "Shetkari123"},
    )
    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": farmer["email"], "password": "WrongPassword1"},
    )
    assert unknown.status_code == wrong_password.status_code == 401
    assert unknown.json()["error"]["message"] == wrong_password.json()["error"]["message"]


def test_me_returns_current_user(client, farmer):
    res = client.get("/api/v1/auth/me", headers=farmer["headers"])
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["user"]["id"] == farmer["user_id"]
    assert data["has_profile"] is True


def test_me_requires_a_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_rejects_a_garbage_token(client):
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert res.status_code == 401


def test_refresh_returns_a_new_token_pair(client, farmer):
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": farmer["refresh"]})
    assert res.status_code == 200
    assert res.json()["data"]["tokens"]["access_token"]


def test_refresh_token_cannot_be_used_as_an_access_token(client, farmer):
    """The `type` claim is what prevents this; without it a long-lived refresh
    token would work anywhere an access token does."""
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {farmer['refresh']}"},
    )
    assert res.status_code == 401


def test_access_token_cannot_be_used_to_refresh(client, farmer):
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": farmer["token"]})
    assert res.status_code == 401
