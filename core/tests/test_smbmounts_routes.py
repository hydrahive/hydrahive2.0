"""Tests für die SMB-Mount-CRUD-Routes.

Auth-Override via dependency_overrides (Muster aus test_teamchat_routes.py).
Kein echtes Mounten — nur die DB/Validierungs-Schicht über die API.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_client(setup_test_env):
    from hydrahive.api import main
    from hydrahive.api.middleware.auth import require_auth

    main.app.dependency_overrides[require_auth] = lambda: ("till", "user")
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides.pop(require_auth, None)


def test_create_and_list(auth_client):
    resp = auth_client.post("/api/smb-mounts", json={
        "name": "nasbackup", "host": "192.168.178.219", "share": "backups",
        "subpath": "hydra",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "nasbackup"
    assert body["mount_state"] == "unmounted"
    assert body["project_id"] is None

    lst = auth_client.get("/api/smb-mounts").json()
    assert any(m["name"] == "nasbackup" for m in lst)


def test_create_rejects_bad_name(auth_client):
    resp = auth_client.post("/api/smb-mounts", json={
        "name": "../evil", "host": "h", "share": "s",
    })
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "mount_name_invalid"


def test_create_rejects_injection_host(auth_client):
    resp = auth_client.post("/api/smb-mounts", json={
        "name": "ok", "host": "1.2.3.4; rm -rf /", "share": "s",
    })
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "mount_host_invalid"


def test_create_rejects_traversal_subpath(auth_client):
    resp = auth_client.post("/api/smb-mounts", json={
        "name": "ok2", "host": "h", "share": "s", "subpath": "../../etc",
    })
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "mount_subpath_invalid"


def test_duplicate_name_conflict(auth_client):
    payload = {"name": "dup", "host": "h", "share": "s"}
    assert auth_client.post("/api/smb-mounts", json=payload).status_code == 201
    resp = auth_client.post("/api/smb-mounts", json=payload)
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "mount_name_taken"


def test_update_and_delete(auth_client):
    created = auth_client.post("/api/smb-mounts", json={
        "name": "edit", "host": "h", "share": "s",
    }).json()
    mid = created["id"]

    upd = auth_client.patch(f"/api/smb-mounts/{mid}", json={"read_only": True})
    assert upd.status_code == 200
    assert upd.json()["read_only"] is True

    assert auth_client.delete(f"/api/smb-mounts/{mid}").status_code == 204
    assert auth_client.get(f"/api/smb-mounts/{mid}").status_code == 404


def test_get_missing_404(auth_client):
    assert auth_client.get("/api/smb-mounts/nope").status_code == 404


def test_credential_must_be_basic(auth_client):
    resp = auth_client.post("/api/smb-mounts", json={
        "name": "withcred", "host": "h", "share": "s",
        "credential": "does-not-exist",
    })
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "mount_credential_invalid"
