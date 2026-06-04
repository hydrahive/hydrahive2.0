"""Health-Ingest-Security: _check_key (timing-safe, fail-closed) + Rate-Limit.

Portiert beim Apple-Health-Modul-Port aus core test_inbound_security (#180, health-Teil).
Die generischen Middleware-Tests (verify_secret, Rate-Limit, WhatsApp) bleiben Core.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException


def test_health_check_key_rejects_wrong(monkeypatch):
    import backend.health_routes as health_routes
    monkeypatch.setattr(health_routes.settings, "health_api_key", "S3CR3T", raising=False)
    with pytest.raises(HTTPException) as e:
        health_routes._check_key("wrong", None, None)
    assert e.value.status_code == 401


def test_health_check_key_accepts_header_bearer_query(monkeypatch):
    import backend.health_routes as health_routes
    monkeypatch.setattr(health_routes.settings, "health_api_key", "S3CR3T", raising=False)
    health_routes._check_key("S3CR3T", None, None)
    health_routes._check_key(None, "Bearer S3CR3T", None)
    health_routes._check_key(None, None, "S3CR3T")


def test_health_check_key_disabled_when_unset(monkeypatch):
    import backend.health_routes as health_routes
    monkeypatch.setattr(health_routes.settings, "health_api_key", "", raising=False)
    with pytest.raises(HTTPException) as e:
        health_routes._check_key("anything", None, None)
    assert e.value.status_code == 403


def test_health_ingest_rate_limited_429(client, monkeypatch):
    monkeypatch.setattr("backend.health_routes.check_rate", lambda *a, **k: (False, 9))
    r = client.post("/api/modules/patientenakte/health-data/ingest", json={})
    assert r.status_code == 429
    assert r.headers.get("Retry-After") == "9"
