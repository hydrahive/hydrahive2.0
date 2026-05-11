"""Tests für /api/analytics-Routen (Issue #130)."""
from __future__ import annotations

from hydrahive.db import llm_calls as llm_calls_db
from hydrahive.db import sessions as sessions_db


def _llm(sid: str, aid: str, uid: str, *, cost: int, prompt: int = 1000,
         completion: int = 100, cache_read: int = 0) -> None:
    llm_calls_db.insert(llm_calls_db.LlmCall(
        session_id=sid, agent_id=aid, user_id=uid,
        provider="anthropic", model="claude-sonnet-4-7",
        temperature=0.7, max_tokens=4096, reasoning_effort=None,
        prompt_tokens=prompt, completion_tokens=completion,
        cache_read_tokens=cache_read, cache_creation_tokens=0,
        stop_reason="end_turn", ttft_ms=None, total_ms=300,
        cost_micros=cost, turn_in_session=1,
    ))


def test_overview_braucht_auth(client):
    r = client.get("/api/analytics/overview")
    assert r.status_code == 401


def test_overview_user_sieht_nur_eigene(client, auth_headers, admin_headers):
    s_user = sessions_db.create(agent_id="test-agent-001", user_id="testuser", title="u").id
    s_other = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="a").id
    _llm(s_user, "test-agent-001", "testuser", cost=500)
    _llm(s_other, "test-agent-001", "admin", cost=9999)

    r = client.get("/api/analytics/overview", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["today"]["cost_micros"] == 500
    # Admin-Session darf nicht in den Top-Cost-Sessions des Users auftauchen
    top_sids = {row["session_id"] for row in data["top_cost_sessions"]}
    assert s_other not in top_sids


def test_overview_admin_sieht_alles(client, admin_headers):
    s_a = sessions_db.create(agent_id="test-agent-001", user_id="testuser", title="x1").id
    s_b = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="x2").id
    _llm(s_a, "test-agent-001", "testuser", cost=300)
    _llm(s_b, "test-agent-001", "admin", cost=400)

    r = client.get("/api/analytics/overview", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    # Admin sieht beide Sessions als heute-Aggregat
    assert data["today"]["cost_micros"] >= 700


def test_session_detail_user_kein_zugriff_auf_fremde_session(client, auth_headers):
    s_other = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="forbidden").id
    r = client.get(f"/api/analytics/session/{s_other}", headers=auth_headers)
    assert r.status_code == 403


def test_session_detail_admin_sieht_fremde(client, admin_headers):
    s = sessions_db.create(agent_id="test-agent-001", user_id="testuser", title="ok").id
    _llm(s, "test-agent-001", "testuser", cost=100)
    r = client.get(f"/api/analytics/session/{s}", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["metrics"]["cost_micros"] == 100
    assert len(data["llm_calls"]) == 1


def test_session_detail_404_bei_unbekannter_session(client, admin_headers):
    r = client.get("/api/analytics/session/does-not-exist", headers=admin_headers)
    assert r.status_code == 404


def test_overview_last_7d_enthaelt_cache_creation_tokens(client, admin_headers):
    """Cache-Hit-Berechnung im Frontend braucht cache_creation_tokens — sonst
    explodiert die Ratio (Bug aus erster #130-Iteration, 14249%)."""
    s = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="cache-7d").id
    llm_calls_db.insert(llm_calls_db.LlmCall(
        session_id=s, agent_id="test-agent-001", user_id="admin",
        provider="anthropic", model="claude-sonnet-4-7",
        temperature=0.7, max_tokens=4096, reasoning_effort=None,
        prompt_tokens=1000, completion_tokens=200,
        cache_read_tokens=50_000, cache_creation_tokens=2000,
        stop_reason="end_turn", ttft_ms=None, total_ms=300,
        cost_micros=300, turn_in_session=1,
    ))
    r = client.get("/api/analytics/overview", headers=admin_headers)
    assert r.status_code == 200
    last_7d = r.json()["last_7d"]
    assert "cache_creation_tokens" in last_7d
    assert last_7d["cache_creation_tokens"] >= 2000


def test_overview_by_model_aufgeschluesselt(client, admin_headers):
    s = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="model-test").id
    # Zwei verschiedene Modelle
    llm_calls_db.insert(llm_calls_db.LlmCall(
        session_id=s, agent_id="test-agent-001", user_id="admin",
        provider="anthropic", model="claude-opus-4-7-20251015",
        temperature=0.7, max_tokens=4096, reasoning_effort=None,
        prompt_tokens=2000, completion_tokens=200,
        cache_read_tokens=0, cache_creation_tokens=0,
        stop_reason="end_turn", ttft_ms=None, total_ms=500,
        cost_micros=5000, turn_in_session=1,
    ))
    _llm(s, "test-agent-001", "admin", cost=100)  # claude-sonnet-4-7

    r = client.get("/api/analytics/overview", headers=admin_headers)
    assert r.status_code == 200
    by_model = r.json()["by_model"]
    models = {row["model"] for row in by_model}
    assert "claude-opus-4-7-20251015" in models
    assert "claude-sonnet-4-7" in models
