"""Farmer profile and farm endpoints."""


def test_get_profile(client, farmer):
    res = client.get("/api/v1/farmer/profile", headers=farmer["headers"])
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["full_name"] == "Test Farmer"
    assert data["district"] == "Nashik"
    assert data["preferred_language"] == "mr"


def test_profile_requires_authentication(client):
    assert client.get("/api/v1/farmer/profile").status_code == 401


def test_partial_update_does_not_blank_omitted_fields(client, farmer):
    """A PUT that mentions only the language must leave the district alone.
    Without exclude_unset this silently wipes the farmer's location."""
    res = client.put(
        "/api/v1/farmer/profile",
        json={"preferred_language": "hi"},
        headers=farmer["headers"],
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["preferred_language"] == "hi"
    assert data["district"] == "Nashik", "untouched field was overwritten"


def test_language_preference_persists(client, farmer):
    client.put(
        "/api/v1/farmer/profile",
        json={"preferred_language": "en"},
        headers=farmer["headers"],
    )
    again = client.get("/api/v1/farmer/profile", headers=farmer["headers"])
    assert again.json()["data"]["preferred_language"] == "en"


def test_invalid_language_is_rejected(client, farmer):
    res = client.put(
        "/api/v1/farmer/profile",
        json={"preferred_language": "fr"},
        headers=farmer["headers"],
    )
    assert res.status_code == 422


def test_invalid_pincode_is_rejected(client, farmer):
    res = client.put(
        "/api/v1/farmer/profile", json={"pincode": "12"}, headers=farmer["headers"]
    )
    assert res.status_code == 422


def test_create_and_list_farms(client, farmer):
    created = client.post(
        "/api/v1/farmer/farms",
        json={
            "name": "Mala che shet",
            "area_value": 2.5,
            "area_unit": "guntha",
            "soil_type": "black",
        },
        headers=farmer["headers"],
    )
    assert created.status_code == 201
    assert created.json()["data"]["area_unit"] == "guntha"

    farms = client.get("/api/v1/farmer/farms", headers=farmer["headers"]).json()["data"]
    assert any(f["name"] == "Mala che shet" for f in farms)


def test_farm_area_must_be_positive(client, farmer):
    res = client.post(
        "/api/v1/farmer/farms",
        json={"name": "Bad farm", "area_value": 0, "area_unit": "acre"},
        headers=farmer["headers"],
    )
    assert res.status_code == 422


def test_invalid_area_unit_is_rejected(client, farmer):
    res = client.post(
        "/api/v1/farmer/farms",
        json={"name": "Bad unit", "area_value": 1, "area_unit": "bigha"},
        headers=farmer["headers"],
    )
    assert res.status_code == 422


def test_farms_are_scoped_to_their_owner(client, farmer):
    client.post(
        "/api/v1/farmer/farms",
        json={"name": "Private field", "area_value": 1.0, "area_unit": "acre"},
        headers=farmer["headers"],
    )
    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "farm_scope@example.com",
            "password": "Shetkari123",
            "full_name": "Other",
        },
    ).json()["data"]
    other_headers = {"Authorization": f"Bearer {other['tokens']['access_token']}"}
    assert client.get("/api/v1/farmer/farms", headers=other_headers).json()["data"] == []


def test_module_registry_marks_only_phase_1_available(client, farmer):
    """Future modules must never be advertised as usable."""
    modules = client.get("/api/v1/modules", headers=farmer["headers"]).json()["data"]
    available = [m for m in modules if m["status"] == "available"]
    assert [m["key"] for m in available] == ["crop_recommendation"]
    # A coming-soon module must not carry a route the UI could link to.
    assert all(m["route"] is None for m in modules if m["status"] == "coming_soon")
