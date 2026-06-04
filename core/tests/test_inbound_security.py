"""Timing-safe Secret-Vergleich + Per-IP Rate-Limit für unauth Inbound-Endpoints
(Issue #180): /api/communication/whatsapp/incoming.

Der Health-Ingest-Teil (_check_key + ingest-Rate-Limit) lebt seit dem
Akte-Modul-Port im Modul (modules/patientenakte/tests/test_health_security.py).
"""
from __future__ import annotations

from hydrahive.api.middleware import inbound_ratelimit as rl
from hydrahive.api.middleware.secret_compare import verify_secret


# --- verify_secret: konstant-zeitig + fail-closed ---------------------------

def test_verify_secret_match():
    assert verify_secret("abc", "abc") is True


def test_verify_secret_mismatch():
    assert verify_secret("abc", "abd") is False


def test_verify_secret_none_provided():
    assert verify_secret(None, "abc") is False


def test_verify_secret_empty_expected_is_fail_closed():
    assert verify_secret("abc", "") is False
    assert verify_secret("abc", None) is False
    assert verify_secret("", "") is False


# --- Rate-Limit: Sliding-Window per Key -------------------------------------

def test_rate_allows_under_limit():
    rl.reset()
    for _ in range(3):
        allowed, _ = rl.check_rate("k", limit=5, window=60)
        assert allowed


def test_rate_blocks_at_limit():
    rl.reset()
    for _ in range(5):
        assert rl.check_rate("k2", limit=5, window=60)[0]
    allowed, retry = rl.check_rate("k2", limit=5, window=60)
    assert allowed is False
    assert retry >= 1


def test_rate_keys_are_isolated():
    rl.reset()
    for _ in range(5):
        rl.check_rate("a", limit=5, window=60)
    assert rl.check_rate("b", limit=5, window=60)[0] is True


def test_rate_window_prunes(monkeypatch):
    rl.reset()
    clock = [1000.0]
    monkeypatch.setattr(rl.time, "time", lambda: clock[0])
    for _ in range(5):
        assert rl.check_rate("k3", limit=5, window=60)[0]
    assert rl.check_rate("k3", limit=5, window=60)[0] is False
    clock[0] += 61
    assert rl.check_rate("k3", limit=5, window=60)[0] is True


# --- Endpoint-Wiring: 401 bei falschem Secret, 429 bei Rate-Limit -----------

def test_wa_incoming_bad_secret_401(client):
    rl.reset()
    r = client.post(
        "/api/communication/whatsapp/incoming",
        json={"target_username": "x", "external_user_id": "y", "text": "hi"},
        headers={"X-HH-Bridge-Secret": "definitely-wrong"},
    )
    assert r.status_code == 401


def test_wa_incoming_rate_limited_429(client, monkeypatch):
    monkeypatch.setattr(
        "hydrahive.api.routes.communication_whatsapp_incoming.check_rate",
        lambda *a, **k: (False, 7),
    )
    r = client.post(
        "/api/communication/whatsapp/incoming",
        json={}, headers={"X-HH-Bridge-Secret": "whatever"},
    )
    assert r.status_code == 429
    assert r.headers.get("Retry-After") == "7"
