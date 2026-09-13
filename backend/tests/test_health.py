"""Health endpoint."""


def test_health_reports_all_dependencies(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    checks = body["data"]["checks"]
    assert checks["database"]["status"] == "available"
    assert "crop_recommendation_model" in checks


def test_health_status_is_ok_when_model_and_db_are_up(client):
    data = client.get("/api/v1/health").json()["data"]
    if data["checks"]["crop_recommendation_model"]["status"] == "available":
        assert data["status"] == "ok"
    else:
        # Model missing must degrade, never take the service down.
        assert data["status"] == "degraded"


def test_root_endpoint(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["data"]["phase"] == 1
