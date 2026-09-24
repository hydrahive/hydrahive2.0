from __future__ import annotations


_SUMMARY = {
    "window_hours": 24,
    "since": "2026-01-01T00:00:00+00:00",
    "until": "2026-01-02T00:00:00+00:00",
    "candidate_rows": 3,
    "messages_observed": 3,
    "sessions_observed": 1,
    "signal_counts": {"completion_claim": 1},
    "signal_subject_counts": {"completion_claim": {"tested": 1}},
    "claim_counts": {"tested": 1},
    "unverified_claim_counts": {},
    "evidence_counts": {"tests_passed": 1},
    "completion_claims": 1,
    "unverified_completion_claims": 0,
    "unverified_rate": 0.0,
    "malformed_metadata": 0,
    "truncated": False,
}


def test_integrity_summary_requires_auth(client):
    response = client.get("/api/system/integrity/summary")

    assert response.status_code == 401


def test_integrity_summary_requires_admin(client, auth_headers):
    response = client.get("/api/system/integrity/summary", headers=auth_headers)

    assert response.status_code == 403


def test_integrity_summary_returns_only_aggregate_admin_data(
    client, admin_headers, monkeypatch,
):
    from hydrahive.api.routes import system_admin

    monkeypatch.setattr(system_admin, "summarize_integrity", lambda hours: {**_SUMMARY, "window_hours": hours})

    response = client.get("/api/system/integrity/summary?hours=48", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["window_hours"] == 48
    assert body["evidence_counts"] == {"tests_passed": 1}
    forbidden = {"content", "message", "arguments", "session_id", "user_id", "agent_id"}
    assert forbidden.isdisjoint(body)


def test_integrity_summary_rejects_unbounded_windows(client, admin_headers):
    assert client.get(
        "/api/system/integrity/summary?hours=0", headers=admin_headers,
    ).status_code == 422
    assert client.get(
        "/api/system/integrity/summary?hours=721", headers=admin_headers,
    ).status_code == 422
