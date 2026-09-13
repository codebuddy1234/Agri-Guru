"""Prediction endpoint, validation boundaries, history and ownership."""

import pytest

from tests.conftest import VALID_PREDICTION_INPUT


def test_predict_returns_a_structured_recommendation(client, farmer):
    res = client.post(
        "/api/v1/crop-recommendation/predict",
        json=VALID_PREDICTION_INPUT,
        headers=farmer["headers"],
    )
    assert res.status_code == 200
    p = res.json()["data"]["prediction"]

    assert p["recommended_crop"]
    assert 0.0 <= p["confidence"] <= 1.0
    assert p["model_version"]
    assert isinstance(p["alternatives"], list)
    # The inputs come back so the UI can explain the result without
    # re-sending or re-deriving them.
    assert p["inputs"]["nitrogen"] == 90


def test_predict_is_deterministic_for_the_same_input(client, farmer):
    """A farmer entering the same values twice must not get different crops;
    that would destroy trust faster than any accuracy shortfall."""
    first = client.post(
        "/api/v1/crop-recommendation/predict",
        json=VALID_PREDICTION_INPUT,
        headers=farmer["headers"],
    ).json()["data"]["prediction"]
    second = client.post(
        "/api/v1/crop-recommendation/predict",
        json=VALID_PREDICTION_INPUT,
        headers=farmer["headers"],
    ).json()["data"]["prediction"]
    assert first["recommended_crop"] == second["recommended_crop"]
    assert first["confidence"] == second["confidence"]


def test_predict_requires_authentication(client):
    res = client.post("/api/v1/crop-recommendation/predict", json=VALID_PREDICTION_INPUT)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_alternatives_are_ranked_and_below_the_top_choice(client, farmer):
    p = client.post(
        "/api/v1/crop-recommendation/predict",
        json=VALID_PREDICTION_INPUT,
        headers=farmer["headers"],
    ).json()["data"]["prediction"]

    probs = [a["probability"] for a in p["alternatives"]]
    assert probs == sorted(probs, reverse=True), "alternatives must be ranked"
    for prob in probs:
        assert prob <= p["confidence"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("ph", 15),          # above the physical maximum
        ("ph", -1),          # below zero
        ("humidity", 120),   # above 100%
        ("humidity", -5),
        ("temperature", 99), # implausible
        ("nitrogen", -5),
        ("rainfall", 9999),
        ("potassium", 5000),
    ],
)
def test_predict_rejects_out_of_range_values(client, farmer, field, value):
    res = client.post(
        "/api/v1/crop-recommendation/predict",
        json={**VALID_PREDICTION_INPUT, field: value},
        headers=farmer["headers"],
    )
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "INVALID_INPUT"
    assert any(d["field"] == field for d in body["error"]["details"])


@pytest.mark.parametrize("field", list(VALID_PREDICTION_INPUT.keys()))
def test_predict_rejects_missing_fields(client, farmer, field):
    payload = {k: v for k, v in VALID_PREDICTION_INPUT.items() if k != field}
    res = client.post(
        "/api/v1/crop-recommendation/predict", json=payload, headers=farmer["headers"]
    )
    assert res.status_code == 422
    assert any(d["field"] == field for d in res.json()["error"]["details"])


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_predict_rejects_nan_and_infinity(client, farmer, literal):
    """NaN passes every >= / <= check silently, so it needs an explicit guard.
    Sent as a raw JSON literal because json.dumps would not produce it."""
    raw = (
        '{"nitrogen":90,"phosphorus":42,"potassium":43,"temperature":20.9,'
        f'"humidity":82.0,"ph":{literal},"rainfall":202.9}}'
    )
    res = client.post(
        "/api/v1/crop-recommendation/predict",
        content=raw,
        headers={**farmer["headers"], "Content-Type": "application/json"},
    )
    assert res.status_code == 422, f"{literal} must be rejected"


def test_predict_rejects_non_numeric_values(client, farmer):
    res = client.post(
        "/api/v1/crop-recommendation/predict",
        json={**VALID_PREDICTION_INPUT, "ph": "acidic"},
        headers=farmer["headers"],
    )
    assert res.status_code == 422


def test_values_outside_training_range_are_flagged_not_rejected(client, farmer):
    """52 C is physically possible but beyond anything in the training data.
    The model extrapolates, and the farmer is told so rather than being given
    a silently confident answer."""
    res = client.post(
        "/api/v1/crop-recommendation/predict",
        json={**VALID_PREDICTION_INPUT, "temperature": 52},
        headers=farmer["headers"],
    )
    assert res.status_code == 200
    assert res.json()["data"]["prediction"]["out_of_training_range"] == ["temperature"]


def test_in_range_values_are_not_flagged(client, farmer):
    res = client.post(
        "/api/v1/crop-recommendation/predict",
        json=VALID_PREDICTION_INPUT,
        headers=farmer["headers"],
    )
    assert res.json()["data"]["prediction"]["out_of_training_range"] == []


# --- history -----------------------------------------------------------------


def test_prediction_is_saved_to_history(client, farmer):
    created = client.post(
        "/api/v1/crop-recommendation/predict",
        json=VALID_PREDICTION_INPUT,
        headers=farmer["headers"],
    ).json()["data"]["prediction"]

    history = client.get(
        "/api/v1/crop-recommendation/history", headers=farmer["headers"]
    ).json()
    assert history["meta"]["total"] >= 1
    assert any(item["id"] == created["id"] for item in history["data"])


def test_history_detail_returns_inputs_and_provenance(client, farmer):
    created = client.post(
        "/api/v1/crop-recommendation/predict",
        json=VALID_PREDICTION_INPUT,
        headers=farmer["headers"],
    ).json()["data"]["prediction"]

    detail = client.get(
        f"/api/v1/crop-recommendation/history/{created['id']}", headers=farmer["headers"]
    )
    assert detail.status_code == 200
    p = detail.json()["data"]["prediction"]
    assert p["inputs"]["ph"] == 6.5
    assert p["model_version"] == created["model_version"]


def test_history_is_newest_first(client, farmer):
    for temp in (20.9, 21.9, 22.9):
        client.post(
            "/api/v1/crop-recommendation/predict",
            json={**VALID_PREDICTION_INPUT, "temperature": temp},
            headers=farmer["headers"],
        )
    items = client.get(
        "/api/v1/crop-recommendation/history", headers=farmer["headers"]
    ).json()["data"]
    timestamps = [i["created_at"] for i in items]
    assert timestamps == sorted(timestamps, reverse=True)


def test_history_pagination(client, farmer):
    for temp in (20.0, 21.0, 22.0):
        client.post(
            "/api/v1/crop-recommendation/predict",
            json={**VALID_PREDICTION_INPUT, "temperature": temp},
            headers=farmer["headers"],
        )
    page = client.get(
        "/api/v1/crop-recommendation/history?limit=2&offset=0", headers=farmer["headers"]
    ).json()
    assert len(page["data"]) == 2
    assert page["meta"]["has_more"] is True


def test_history_requires_authentication(client):
    assert client.get("/api/v1/crop-recommendation/history").status_code == 401


def test_history_detail_rejects_a_malformed_id(client, farmer):
    res = client.get(
        "/api/v1/crop-recommendation/history/not-a-uuid", headers=farmer["headers"]
    )
    assert res.status_code == 422


def test_unknown_prediction_id_returns_404(client, farmer):
    res = client.get(
        "/api/v1/crop-recommendation/history/00000000-0000-0000-0000-000000000000",
        headers=farmer["headers"],
    )
    assert res.status_code == 404


# --- isolation between farmers ------------------------------------------------


def test_a_farmer_cannot_read_another_farmers_prediction(client, farmer):
    """Returns 404, not 403: a 403 would confirm the record exists."""
    mine = client.post(
        "/api/v1/crop-recommendation/predict",
        json=VALID_PREDICTION_INPUT,
        headers=farmer["headers"],
    ).json()["data"]["prediction"]

    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "intruder_isolation@example.com",
            "password": "Shetkari123",
            "full_name": "Other Farmer",
        },
    ).json()["data"]
    other_headers = {"Authorization": f"Bearer {other['tokens']['access_token']}"}

    res = client.get(
        f"/api/v1/crop-recommendation/history/{mine['id']}", headers=other_headers
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_history_only_shows_your_own_predictions(client, farmer):
    client.post(
        "/api/v1/crop-recommendation/predict",
        json=VALID_PREDICTION_INPUT,
        headers=farmer["headers"],
    )
    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "separate_history@example.com",
            "password": "Shetkari123",
            "full_name": "Separate Farmer",
        },
    ).json()["data"]
    other_headers = {"Authorization": f"Bearer {other['tokens']['access_token']}"}

    assert (
        client.get("/api/v1/crop-recommendation/history", headers=other_headers).json()[
            "meta"
        ]["total"]
        == 0
    )


def test_a_farmer_cannot_attach_another_farmers_farm(client, farmer):
    farm = client.post(
        "/api/v1/farmer/farms",
        json={"name": "My field", "area_value": 2.0, "area_unit": "acre"},
        headers=farmer["headers"],
    ).json()["data"]

    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "farm_thief@example.com",
            "password": "Shetkari123",
            "full_name": "Other Farmer",
        },
    ).json()["data"]
    other_headers = {"Authorization": f"Bearer {other['tokens']['access_token']}"}

    res = client.post(
        "/api/v1/crop-recommendation/predict",
        json={**VALID_PREDICTION_INPUT, "farm_id": farm["id"]},
        headers=other_headers,
    )
    assert res.status_code == 404


def test_model_info_carries_the_honesty_caveat(client, farmer):
    """The caveat travels with the metrics through the API, so it cannot be
    quoted as a bare accuracy figure without the context."""
    res = client.get("/api/v1/crop-recommendation/model-info", headers=farmer["headers"])
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["n_classes"] == 22
    assert "not" in data["caveat"].lower()
    assert data["metrics"]["holdout_accuracy"] > 0
