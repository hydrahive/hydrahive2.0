"""Projektrolle „read“ darf nichts schreiben (Rollenmodell read < write < admin, _members_model.ROLES).

Befund 12.10.2026 (Review-Folge): Git-, Samba-, Mount- und Server-Routen prüften nur „ist Mitglied“
(is_member) statt der Mindestrolle. Ein Lese-Mitglied konnte so committen, pushen, Repos löschen,
Samba umschalten und Mounts/Server zuweisen. Diese Tests halten fest: read → 403 project_no_access,
und zwar bevor irgendetwas passiert (der Rollencheck kommt vor der Arbeit).
"""
from __future__ import annotations

import pytest

from tests.conftest import error_code


@pytest.fixture
def read_project(client, admin_headers):
    r = client.post("/api/projects", headers=admin_headers,
                    json={"name": "Nur-Lesen", "llm_model": "test/model", "members": []})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    r = client.post(f"/api/projects/{pid}/members/testuser", headers=admin_headers, json={"role": "read"})
    assert r.status_code == 200, r.text
    yield pid
    client.delete(f"/api/projects/{pid}", headers=admin_headers)


SCHREIBEND = [
    ("post", "/git/repos/clone", {"url": "https://example.org/x.git", "name": "x"}),
    ("post", "/git/repos/init", {"name": "neu"}),
    ("put", "/git/repos/neu/config", {"remote_url": "https://example.org/y.git"}),
    ("post", "/git/repos/neu/commit", {"message": "m"}),
    ("post", "/git/repos/neu/push", {}),
    ("post", "/git/repos/neu/pull", {}),
    ("delete", "/git/repos/neu", None),
    ("post", "/git/repos/neu/gitea/create", {}),
    ("post", "/git/repos/neu/gitea/push", {}),
    ("post", "/git/repos/neu/gitea/pull", {}),
    ("put", "/samba", {"enabled": True}),
    ("post", "/mounts/assign", {"id": "m1"}),
    ("delete", "/mounts/m1", None),
    ("post", "/servers/assign", {"kind": "vm", "id": "v1"}),
    ("delete", "/servers/vm/v1", None),
]


@pytest.mark.parametrize(("method", "suffix", "body"), SCHREIBEND, ids=[f"{m} {s}" for m, s, _ in SCHREIBEND])
def test_lese_mitglied_darf_nicht_schreiben(client, auth_headers, read_project, method, suffix, body):
    kw = {"headers": auth_headers}
    if body is not None:
        kw["json"] = body
    r = getattr(client, method)(f"/api/projects/{read_project}{suffix}", **kw)
    assert r.status_code == 403 and error_code(r) == "project_no_access", (r.status_code, r.text[:200])


LESEND = ["/git/repos", "/samba", "/mounts", "/servers", "/mounts/available", "/servers/available"]


@pytest.mark.parametrize("suffix", LESEND)
def test_lese_mitglied_darf_weiter_lesen(client, auth_headers, read_project, suffix):
    r = client.get(f"/api/projects/{read_project}{suffix}", headers=auth_headers)
    assert r.status_code != 403, (suffix, r.status_code, r.text[:200])
