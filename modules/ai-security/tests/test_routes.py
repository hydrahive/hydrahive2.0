"""API-Vertrag, Authentifizierung und User-Isolation."""
from __future__ import annotations

from unittest.mock import AsyncMock

from backend import routes
from backend.aig_client import AigError


class FakeAigClient:
    health = AsyncMock(return_value=None)
    create_infra_scan = AsyncMock(return_value="upstream-1")


def test_health_requires_auth(client):
    response = client.get("/api/modules/ai-security/health")
    assert response.status_code == 401


def test_targets_only_expose_allowlist(client, alice):
    response = client.get("/api/modules/ai-security/targets", headers=alice)
    assert response.status_code == 200
    assert response.json() == ["http://127.0.0.1:11434"]


def test_create_scan_returns_202_and_owner(client, alice, monkeypatch):
    monkeypatch.setattr(routes, "AigClient", FakeAigClient)
    response = client.post(
        "/api/modules/ai-security/scans",
        json={"scan_type": "infra", "target_url": "http://127.0.0.1:11434"},
        headers=alice,
    )
    assert response.status_code == 202
    assert response.json()["status"] == "running"
    assert response.json()["upstream_session_id"] == "upstream-1"


def test_scan_target_is_validated_before_upstream_call(client, alice, monkeypatch):
    class FreshFake:
        create_infra_scan = AsyncMock()

    fake = FreshFake()
    monkeypatch.setattr(routes, "AigClient", lambda: fake)
    response = client.post(
        "/api/modules/ai-security/scans",
        json={"scan_type": "infra", "target_url": "http://127.0.0.1:11435"},
        headers=alice,
    )
    assert response.status_code == 422
    fake.create_infra_scan.assert_not_awaited()


def test_users_cannot_read_each_others_scans(client, alice, bob, monkeypatch):
    monkeypatch.setattr(routes, "AigClient", FakeAigClient)
    response = client.post(
        "/api/modules/ai-security/scans",
        json={"target_url": "http://127.0.0.1:11434"},
        headers=alice,
    )
    scan_id = response.json()["id"]
    hidden = client.get(f"/api/modules/ai-security/scans/{scan_id}", headers=bob)
    assert hidden.status_code == 403


def test_upstream_failure_is_not_leaked(client, alice, monkeypatch):
    class FailingClient:
        create_infra_scan = AsyncMock(side_effect=AigError("aig_unreachable"))

    monkeypatch.setattr(routes, "AigClient", FailingClient)
    response = client.post(
        "/api/modules/ai-security/scans",
        json={"target_url": "http://127.0.0.1:11434"},
        headers=alice,
    )
    assert response.status_code == 503
    assert "secret-token" not in response.text
