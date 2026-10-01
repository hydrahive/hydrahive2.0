"""API der Hintergrund-Aufträge: Besitzer-Prüfung, Abbrechen, Zustellen."""
from __future__ import annotations

from hydrahive.db import delegations as delegations_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import delegation_delivery
from tests.conftest import error_code


def _setup(owner: str = "admin") -> tuple[str, dict]:
    sid = sessions_db.create(agent_id="test-agent-001", user_id=owner, title="api").id
    d = delegations_db.create(session_id=sid, agent_id="test-agent-001", user_id=owner,
                              target_agent_id="t", target_name="Prüfer", task="prüf das",
                              state_id=f"st-api-{sid}", depth=1, timeout_seconds=600)
    return sid, d


def test_list_shows_running_delegation(client, admin_headers):
    sid, d = _setup()
    r = client.get(f"/api/sessions/{sid}/delegations", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["delegations"][0]["id"] == d["id"]
    assert body["delegations"][0]["status"] == "running"
    assert body["delegations"][0]["rounds"] == 0
    assert body["undelivered"] is False


def test_foreign_user_gets_403(client, auth_headers):
    sid, d = _setup(owner="admin")
    r = client.get(f"/api/sessions/{sid}/delegations", headers=auth_headers)
    assert r.status_code == 403
    r = client.post(f"/api/sessions/{sid}/delegations/{d['id']}/cancel", headers=auth_headers)
    assert r.status_code == 403
    assert delegations_db.get(d["id"])["status"] == "running"


def test_cancel_requires_matching_session(client, admin_headers):
    sid_a, _ = _setup()
    _sid_b, d_b = _setup()
    r = client.post(f"/api/sessions/{sid_a}/delegations/{d_b['id']}/cancel", headers=admin_headers)
    assert r.status_code == 404 and error_code(r) == "delegation_not_found"
    assert delegations_db.get(d_b["id"])["status"] == "running"


def test_cancel_marks_cancelled(client, admin_headers):
    sid, d = _setup()
    r = client.post(f"/api/sessions/{sid}/delegations/{d['id']}/cancel", headers=admin_headers)
    assert r.json() == {"cancelled": True}
    assert delegations_db.get(d["id"])["status"] == "cancelled"


def test_deliver_now_starts_run_even_when_paused(client, admin_headers):
    sid, d = _setup()
    delegations_db.complete_if_running(d["id"], "done", "fertig")
    started: list = []
    delegation_delivery.configure(lambda s, t, **kw: started.append(s))
    delegation_delivery.pause(sid)
    try:
        r = client.get(f"/api/sessions/{sid}/delegations", headers=admin_headers)
        assert r.json()["undelivered"] is True and r.json()["paused"] is True
        r = client.post(f"/api/sessions/{sid}/delegations/deliver", headers=admin_headers)
        assert r.json() == {"started": True}
    finally:
        delegation_delivery.configure(None)
        delegation_delivery.resume(sid)
    assert started == [sid]
