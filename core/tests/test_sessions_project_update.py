"""PATCH /api/sessions/{id} mit project_id — setzt das aktive Projekt + Authz.

Das aktive Projekt bestimmt das Arbeitsverzeichnis des Runs (Buddy/Master im
Projekt-Repo). Eine Session darf nur an Projekte geheftet werden, auf die der
User Zugriff hat.
"""
from __future__ import annotations


def _new_session(client, auth_headers) -> str:
    r = client.post("/api/sessions", json={"agent_id": "test-agent-001", "title": "t"}, headers=auth_headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_update_session_sets_own_project(client, auth_headers):
    from hydrahive.projects import config as pc

    sid = _new_session(client, auth_headers)
    proj = pc.create(name="ProjX", llm_model="claude-sonnet-4-6", created_by="testuser")

    r = client.patch(f"/api/sessions/{sid}", json={"project_id": proj["id"]}, headers=auth_headers)

    assert r.status_code == 200, r.text
    assert r.json()["project_id"] == proj["id"]


def test_update_session_can_clear_project(client, auth_headers):
    from hydrahive.projects import config as pc

    sid = _new_session(client, auth_headers)
    proj = pc.create(name="ProjY", llm_model="claude-sonnet-4-6", created_by="testuser")
    client.patch(f"/api/sessions/{sid}", json={"project_id": proj["id"]}, headers=auth_headers)

    r = client.patch(f"/api/sessions/{sid}", json={"project_id": ""}, headers=auth_headers)

    assert r.status_code == 200, r.text
    assert r.json()["project_id"] is None


def test_update_session_rejects_foreign_project(client, auth_headers):
    from hydrahive.projects import config as pc

    sid = _new_session(client, auth_headers)
    foreign = pc.create(name="Foreign", llm_model="claude-sonnet-4-6", created_by="someone_else")

    r = client.patch(f"/api/sessions/{sid}", json={"project_id": foreign["id"]}, headers=auth_headers)

    assert r.status_code == 403, r.text


def test_update_session_unknown_project_404(client, auth_headers):
    sid = _new_session(client, auth_headers)

    r = client.patch(f"/api/sessions/{sid}", json={"project_id": "ghost-id"}, headers=auth_headers)

    assert r.status_code == 404, r.text
