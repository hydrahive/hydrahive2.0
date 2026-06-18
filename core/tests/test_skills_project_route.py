"""Skills-REST-Route: project-Scope braucht Projekt-Mitgliedschaft.

Ohne Auth-Check könnte jeder User Skills in fremde Projekte schreiben (Tor,
das durch die Aufnahme von 'project' in SkillScope sonst offenstünde)."""
from __future__ import annotations


def test_non_member_cannot_write_project_skill(client, auth_headers, monkeypatch):
    from hydrahive.projects import config as pc
    monkeypatch.setattr(pc, "get", lambda pid: {"id": pid, "owner": "someone_else", "members": []})
    r = client.post("/api/skills/project?owner=proj-x", headers=auth_headers, json={
        "name": "x", "description": "d", "when_to_use": "w", "body": "b",
    })
    assert r.status_code == 403


def test_member_can_write_project_skill(client, auth_headers, monkeypatch):
    from hydrahive.projects import config as pc
    # auth_headers == testuser; als Owner zugelassen
    monkeypatch.setattr(pc, "get", lambda pid: {"id": pid, "owner": "testuser", "members": []})
    r = client.post("/api/skills/project?owner=proj-x", headers=auth_headers, json={
        "name": "shared", "description": "d", "when_to_use": "w", "body": "b",
    })
    assert r.status_code == 201
