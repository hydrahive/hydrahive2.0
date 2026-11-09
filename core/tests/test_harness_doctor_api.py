def test_harness_doctor_requires_auth(client):
    assert client.get("/api/system/harness-doctor").status_code == 401


def test_harness_doctor_requires_admin(client, auth_headers):
    assert client.get("/api/system/harness-doctor", headers=auth_headers).status_code == 403


def test_harness_doctor_returns_read_only_aggregate(client, admin_headers, monkeypatch):
    from hydrahive.api.routes import harness_doctor

    monkeypatch.setattr(harness_doctor, "run_doctor", lambda hours: {
        "window_hours": hours, "overall_score": 80, "lowest_dimension": "state",
        "dimensions": [], "priorities": [], "agent_outliers": [], "snapshot": {}, "notes": [],
    })
    response = client.get("/api/system/harness-doctor?hours=24", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["window_hours"] == 24
    assert response.json()["overall_score"] == 80


def test_harness_doctor_real_collector_stays_aggregate(client, admin_headers):
    response = client.get("/api/system/harness-doctor?hours=1", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["overall_score"] <= 100
    serialized = response.text.lower()
    for forbidden in ("password", "api_key", "bearer ", "tool_result", "message_content"):
        assert forbidden not in serialized


def test_harness_doctor_rejects_unbounded_window(client, admin_headers):
    assert client.get("/api/system/harness-doctor?hours=0", headers=admin_headers).status_code == 422
    assert client.get("/api/system/harness-doctor?hours=721", headers=admin_headers).status_code == 422
