"""Tests für die Projekt-Zuweisung von SMB-Mounts.

Kein echter Fileserver — beim Assign gegen einen toten Host muss der
Fehler-Pfad sauber zurückrollen (502, state=error, project_id=NULL).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def ctx(setup_test_env):
    from hydrahive.api import main
    from hydrahive.api.middleware.auth import require_auth
    from hydrahive.projects import config as project_config

    proj = project_config.create(
        name="mounttest", llm_model="anthropic/claude-sonnet-4",
        created_by="testuser", members=["testuser"],
    )
    main.app.dependency_overrides[require_auth] = lambda: ("testuser", "user")
    with TestClient(main.app) as c:
        yield c, proj["id"]
    main.app.dependency_overrides.pop(require_auth, None)


def _make_mount(c, name, host="10.255.255.1"):
    resp = c.post("/api/smb-mounts", json={
        "name": name, "host": host, "share": "backups",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_available_lists_unassigned(ctx):
    c, pid = ctx
    m = _make_mount(c, "avail1")
    avail = c.get(f"/api/projects/{pid}/mounts/available").json()
    assert any(x["id"] == m["id"] for x in avail)


def test_assign_dead_host_rolls_back(ctx):
    c, pid = ctx
    m = _make_mount(c, "rollback1")
    # toter Host → mount.cifs failt → 502 und sauberer Rollback
    resp = c.post(f"/api/projects/{pid}/mounts/assign", json={"id": m["id"]})
    assert resp.status_code == 502, resp.text

    after = c.get(f"/api/smb-mounts/{m['id']}").json()
    assert after["project_id"] is None          # zurückgerollt
    assert after["mount_state"] == "error"
    assert after["last_error_code"]             # fehlercode gesetzt


def test_assign_missing_mount_404(ctx):
    c, pid = ctx
    resp = c.post(f"/api/projects/{pid}/mounts/assign", json={"id": "nope"})
    assert resp.status_code == 404


def test_unassign_not_assigned_404(ctx):
    c, pid = ctx
    m = _make_mount(c, "unassign1")
    resp = c.delete(f"/api/projects/{pid}/mounts/{m['id']}")
    assert resp.status_code == 404


def test_list_assigned_empty(ctx):
    c, pid = ctx
    assert c.get(f"/api/projects/{pid}/mounts").json() == []
