"""#74: Projekt-Audit-Log — log() schreibt, list_for_project() filtert/sortiert,
und ein fehlerhafter Eintrag bricht die Hauptoperation NICHT (nur Logging).
"""
from __future__ import annotations

import logging

import pytest

from hydrahive.projects import audit


@pytest.fixture(autouse=True)
def _ensure_db(setup_test_env):
    from hydrahive.db import init_db
    from hydrahive.db.connection import db
    init_db()
    yield
    with db() as conn:
        conn.execute("DELETE FROM project_audit_log")


def test_log_writes_retrievable_entry():
    audit.log("p1", "till", "member_added", target="alice")
    rows = audit.list_for_project("p1")
    assert len(rows) == 1
    assert rows[0]["user"] == "till"
    assert rows[0]["action"] == "member_added"
    assert rows[0]["target"] == "alice"


def test_list_filters_by_action():
    audit.log("p1", "till", "member_added", target="alice")
    audit.log("p1", "till", "project_updated", details={"name": "X"})
    rows = audit.list_for_project("p1", action="member_added")
    assert [r["action"] for r in rows] == ["member_added"]


def test_list_filters_by_user():
    audit.log("p1", "till", "member_added", target="a")
    audit.log("p1", "bob", "member_removed", target="a")
    rows = audit.list_for_project("p1", user_id="bob")
    assert [r["user"] for r in rows] == ["bob"]


def test_list_isolates_project_and_orders_newest_first():
    audit.log("p1", "till", "project_updated")
    audit.log("p2", "till", "project_updated")
    audit.log("p1", "till", "member_added", target="a")
    rows = audit.list_for_project("p1")
    assert len(rows) == 2
    assert rows[0]["action"] == "member_added"  # neuester zuerst


def test_log_never_raises_on_unserializable_details(caplog):
    with caplog.at_level(logging.WARNING):
        audit.log("p1", "till", "weird", details={"bad": {1, 2}})  # set → json.dumps TypeError
    # kein Raise; stattdessen Warnung
    assert any(r.levelno >= logging.WARNING for r in caplog.records)


def test_get_project_audit_route(client, admin_headers):
    r = client.post("/api/projects", json={"name": "AuditProj", "llm_model": "claude-sonnet-4-6"}, headers=admin_headers)
    assert r.status_code == 201
    pid = r.json()["id"]
    audit.log(pid, "admin", "member_added", target="alice")
    r2 = client.get(f"/api/projects/{pid}/audit", headers=admin_headers)
    assert r2.status_code == 200
    data = r2.json()
    assert data["count"] == 1
    assert data["entries"][0]["action"] == "member_added"
    assert data["entries"][0]["target"] == "alice"


def test_get_project_audit_filter_by_action(client, admin_headers):
    r = client.post("/api/projects", json={"name": "AuditProj2", "llm_model": "claude-sonnet-4-6"}, headers=admin_headers)
    pid = r.json()["id"]
    audit.log(pid, "admin", "member_added", target="a")
    audit.log(pid, "admin", "project_updated")
    r2 = client.get(f"/api/projects/{pid}/audit?action=project_updated", headers=admin_headers)
    assert r2.status_code == 200
    assert [e["action"] for e in r2.json()["entries"]] == ["project_updated"]


def test_member_route_hooks_write_audit_with_actor(client, admin_headers):
    r = client.post("/api/projects", json={"name": "HookProj", "llm_model": "claude-sonnet-4-6"}, headers=admin_headers)
    pid = r.json()["id"]
    assert client.post(f"/api/projects/{pid}/members/testuser", headers=admin_headers).status_code == 200
    assert client.delete(f"/api/projects/{pid}/members/testuser", headers=admin_headers).status_code == 200
    entries = client.get(f"/api/projects/{pid}/audit", headers=admin_headers).json()["entries"]
    actions = [e["action"] for e in entries]
    assert "member_added" in actions and "member_removed" in actions
    added = next(e for e in entries if e["action"] == "member_added")
    assert added["user"] == "admin" and added["target"] == "testuser"


def test_project_update_hook_writes_audit(client, admin_headers):
    r = client.post("/api/projects", json={"name": "UpdProj", "llm_model": "claude-sonnet-4-6"}, headers=admin_headers)
    pid = r.json()["id"]
    assert client.patch(f"/api/projects/{pid}", json={"description": "neu"}, headers=admin_headers).status_code == 200
    entries = client.get(f"/api/projects/{pid}/audit", headers=admin_headers).json()["entries"]
    assert any(e["action"] == "project_updated" for e in entries)
