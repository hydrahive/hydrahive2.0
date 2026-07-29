"""Skills-REST-Route: project-Scope braucht Projekt-Mitgliedschaft.

Ohne Auth-Check könnte jeder User Skills in fremde Projekte schreiben (Tor,
das durch die Aufnahme von 'project' in SkillScope sonst offenstünde)."""
from __future__ import annotations


def test_non_member_cannot_write_project_skill(client, auth_headers, monkeypatch):
    from hydrahive.projects import config as pc
    monkeypatch.setattr(pc, "get", lambda pid: {"id": pid, "created_by": "someone_else", "members": []})
    r = client.post("/api/skills/project?owner=proj-x", headers=auth_headers, json={
        "name": "x", "description": "d", "when_to_use": "w", "body": "b",
    })
    assert r.status_code == 403


def test_read_member_cannot_write_project_skill(client, auth_headers, monkeypatch):
    from hydrahive.projects import config as pc
    # testuser ist nur read-Member -> darf keine Skills schreiben.
    monkeypatch.setattr(pc, "get", lambda pid: {
        "id": pid, "created_by": "boss",
        "members": [{"username": "testuser", "role": "read"}],
    })
    r = client.post("/api/skills/project?owner=proj-x", headers=auth_headers, json={
        "name": "x", "description": "d", "when_to_use": "w", "body": "b",
    })
    assert r.status_code == 403


def test_member_can_write_project_skill(client, auth_headers, monkeypatch):
    from hydrahive.projects import config as pc
    # auth_headers == testuser; created_by == Owner -> implizit admin, darf schreiben.
    monkeypatch.setattr(pc, "get", lambda pid: {"id": pid, "created_by": "testuser", "members": []})
    r = client.post("/api/skills/project?owner=proj-x", headers=auth_headers, json={
        "name": "shared", "description": "d", "when_to_use": "w", "body": "b",
    })
    assert r.status_code == 201


def test_write_member_can_write_project_skill(client, auth_headers, monkeypatch):
    from hydrahive.projects import config as pc
    monkeypatch.setattr(pc, "get", lambda pid: {
        "id": pid, "created_by": "boss",
        "members": [{"username": "testuser", "role": "write"}],
    })
    r = client.post("/api/skills/project?owner=proj-x", headers=auth_headers, json={
        "name": "shared2", "description": "d", "when_to_use": "w", "body": "b",
    })
    assert r.status_code == 201
