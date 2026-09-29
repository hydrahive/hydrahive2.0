"""Admin-API für Gruppen und Freigaben (Plan Tasks 2.1, 2.2)."""
from __future__ import annotations

import pytest

from hydrahive.access import store
from tests._access_rows import _own_access_rows  # noqa: F401  (autouse)

_ADMIN_ROUTES = [
    ("get", "/api/access/groups", None),
    ("post", "/api/access/groups", {"name": "x"}),
    ("patch", "/api/access/groups/g", {"name": "y"}),
    ("delete", "/api/access/groups/g", None),
    ("put", "/api/access/groups/g/members/u", None),
    ("delete", "/api/access/groups/g/members/u", None),
    ("get", "/api/access/capabilities", None),
    ("put", "/api/access/grants", {"capability": "core.vms", "subject_type": "everyone",
                                   "subject_id": "", "level": "use"}),
    ("delete", "/api/access/grants?capability=core.vms&subject_type=everyone", None),
]


@pytest.mark.parametrize("method,path,body", _ADMIN_ROUTES)
def test_non_admin_forbidden(client, auth_headers, method, path, body):
    kwargs = {"headers": auth_headers}
    if body is not None:
        kwargs["json"] = body
    r = client.request(method.upper(), path, **kwargs)
    assert r.status_code == 403, (method, path, r.status_code)


def _uid(client, admin_headers, name="testuser") -> str:
    users = client.get("/api/users", headers=admin_headers).json()
    return next(u["user_id"] for u in users if u["username"] == name)


def test_group_crud(client, admin_headers):
    r = client.post("/api/access/groups", json={"name": "Routen-G", "description": "d"},
                    headers=admin_headers)
    assert r.status_code == 201, r.text
    gid = r.json()["id"]
    names = [g["name"] for g in client.get("/api/access/groups", headers=admin_headers).json()]
    assert "Routen-G" in names
    r = client.patch(f"/api/access/groups/{gid}", json={"name": "Routen-G2"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["name"] == "Routen-G2"
    assert client.delete(f"/api/access/groups/{gid}", headers=admin_headers).status_code == 204
    assert client.delete(f"/api/access/groups/{gid}", headers=admin_headers).status_code == 404


def test_duplicate_group_conflict(client, admin_headers):
    client.post("/api/access/groups", json={"name": "Dup-R"}, headers=admin_headers)
    r = client.post("/api/access/groups", json={"name": "Dup-R"}, headers=admin_headers)
    assert r.status_code == 409


def test_members(client, admin_headers):
    gid = client.post("/api/access/groups", json={"name": "Mitgl-R"}, headers=admin_headers).json()["id"]
    uid = _uid(client, admin_headers)
    assert client.put(f"/api/access/groups/{gid}/members/{uid}", headers=admin_headers).status_code == 204
    g = client.get(f"/api/access/groups/{gid}", headers=admin_headers).json()
    assert g["members"] == [{"user_id": uid, "username": "testuser"}]
    assert client.delete(f"/api/access/groups/{gid}/members/{uid}", headers=admin_headers).status_code == 204
    assert client.get(f"/api/access/groups/{gid}", headers=admin_headers).json()["members"] == []


def test_member_unknown_user_404(client, admin_headers):
    gid = client.post("/api/access/groups", json={"name": "Unb-R"}, headers=admin_headers).json()["id"]
    r = client.put(f"/api/access/groups/{gid}/members/gibt-es-nicht", headers=admin_headers)
    assert r.status_code == 404


def test_capabilities_lists_core_and_grants(client, admin_headers):
    uid = _uid(client, admin_headers)
    r = client.put("/api/access/grants", headers=admin_headers, json={
        "capability": "core.vms", "subject_type": "user", "subject_id": uid, "level": "use"})
    assert r.status_code == 204, r.text
    data = client.get("/api/access/capabilities", headers=admin_headers).json()
    vms = next(c for c in data["capabilities"] if c["id"] == "core.vms")
    assert vms["default"] == "admin_only" and vms["module_id"] == ""
    assert {"subject_type": "user", "subject_id": uid, "level": "use"} in vms["grants"]
    assert any(u["username"] == "testuser" for u in data["users"])
    r = client.delete("/api/access/grants", headers=admin_headers, params={
        "capability": "core.vms", "subject_type": "user", "subject_id": uid})
    assert r.status_code == 204
    assert store.audit_for("cap:core.vms")[-1]["action"] == "revoke"


def test_grant_unknown_capability_400(client, admin_headers):
    r = client.put("/api/access/grants", headers=admin_headers, json={
        "capability": "module.gibtsnicht", "subject_type": "everyone", "subject_id": "", "level": "use"})
    assert r.status_code == 400


def test_grant_invalid_subject_400(client, admin_headers):
    r = client.put("/api/access/grants", headers=admin_headers, json={
        "capability": "core.vms", "subject_type": "user", "subject_id": "", "level": "use"})
    assert r.status_code == 400


def test_grant_unknown_group_404(client, admin_headers):
    r = client.put("/api/access/grants", headers=admin_headers, json={
        "capability": "core.vms", "subject_type": "group", "subject_id": "nope", "level": "use"})
    assert r.status_code == 404


def test_audit_records_admin_user_id(client, admin_headers):
    gid = client.post("/api/access/groups", json={"name": "Aud-R"}, headers=admin_headers).json()["id"]
    admin_uid = _uid(client, admin_headers, "admin")
    assert store.audit_for(f"group:{gid}")[0]["actor_id"] == admin_uid


def test_revoke_requires_consistent_subject(client, admin_headers):
    r = client.delete("/api/access/grants", headers=admin_headers,
                      params={"capability": "core.vms", "subject_type": "user"})
    assert r.status_code == 400
