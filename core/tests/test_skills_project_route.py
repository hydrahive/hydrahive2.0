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


def _projekt_skill(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    from hydrahive.skills.loader import save_skill
    from hydrahive.skills.models import Skill
    monkeypatch.setattr(settings, "data_dir", tmp_path, raising=False)
    save_skill(Skill(name="geteilt", description="d", when_to_use="w", body="b",
                     scope="project", owner="proj-x"))


def test_read_member_sieht_projekt_bibliothek(client, auth_headers, monkeypatch, tmp_path):
    """Projekt-Skills sind für Mitglieder sichtbar (Liste im Projekt-Cockpit, MED-2)."""
    from hydrahive.projects import config as pc
    _projekt_skill(tmp_path, monkeypatch)
    monkeypatch.setattr(pc, "get", lambda pid: {
        "id": pid, "created_by": "boss", "members": [{"username": "testuser", "role": "read"}],
    })
    r = client.get("/api/skills?project_id=proj-x", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert [(s["name"], s["scope"], s["owner"]) for s in r.json()] == [("geteilt", "project", "proj-x")]


def test_nicht_mitglied_sieht_projekt_bibliothek_nicht(client, auth_headers, monkeypatch, tmp_path):
    from hydrahive.projects import config as pc
    _projekt_skill(tmp_path, monkeypatch)
    monkeypatch.setattr(pc, "get", lambda pid: {"id": pid, "created_by": "boss", "members": []})
    r = client.get("/api/skills?project_id=proj-x", headers=auth_headers)
    assert r.status_code == 403


def test_read_member_kann_projekt_skill_lesen(client, auth_headers, monkeypatch, tmp_path):
    from hydrahive.projects import config as pc
    _projekt_skill(tmp_path, monkeypatch)
    monkeypatch.setattr(pc, "get", lambda pid: {
        "id": pid, "created_by": "boss", "members": [{"username": "testuser", "role": "read"}],
    })
    r = client.get("/api/skills/project/geteilt?owner=proj-x", headers=auth_headers)
    assert r.status_code == 200, r.text
