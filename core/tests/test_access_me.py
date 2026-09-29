"""/api/access/me und Aufräumen beim Löschen eines Nutzers (Plan Tasks 2.3, 2.4)."""
from __future__ import annotations

from hydrahive.access import grants, store
from hydrahive.db.connection import db
from tests._access_rows import _own_access_rows  # noqa: F401  (autouse)


def _uid(client, admin_headers, name: str) -> str:
    users = client.get("/api/users", headers=admin_headers).json()
    return next(u["user_id"] for u in users if u["username"] == name)


def test_me_requires_login(client):
    assert client.get("/api/access/me").status_code == 401


def test_me_for_admin(client, admin_headers):
    data = client.get("/api/access/me", headers=admin_headers).json()
    assert data["admin"] is True
    assert data["capabilities"]["core.vms"] == "manage"


def test_me_for_user_lists_own_grants_and_groups(client, auth_headers, admin_headers):
    uid = _uid(client, admin_headers, "testuser")
    g = store.create_group("Me-Gruppe", "", actor_id="adm")
    store.add_member(g["id"], uid, actor_id="adm")
    grants.grant("core.containers", "group", g["id"], "use", actor_id="adm")
    data = client.get("/api/access/me", headers=auth_headers).json()
    assert data["admin"] is False
    assert data["capabilities"].get("core.containers") == "use"
    assert "core.vms" not in data["capabilities"]
    assert {"id": g["id"], "name": "Me-Gruppe"} in data["groups"]
    assert "declared" in data and "core.vms" in data["declared"]


def test_delete_user_purges_memberships_and_grants(client, admin_headers):
    r = client.post("/api/users", headers=admin_headers,
                    json={"username": "wegdamit", "password": "testpass123", "role": "user"})
    assert r.status_code in (200, 201), r.text
    uid = _uid(client, admin_headers, "wegdamit")
    g = store.create_group("Purge-G", "", actor_id="adm")
    store.add_member(g["id"], uid, actor_id="adm")
    grants.grant("core.vms", "user", uid, "use", actor_id="adm")

    assert client.delete("/api/users/wegdamit", headers=admin_headers).status_code == 204

    with db() as c:
        left_members = c.execute("SELECT COUNT(*) FROM access_group_members WHERE user_id = ?",
                                 (uid,)).fetchone()[0]
        left_grants = c.execute(
            "SELECT COUNT(*) FROM access_capability_grants WHERE subject_type='user' AND subject_id = ?",
            (uid,)).fetchone()[0]
    assert left_members == 0 and left_grants == 0
    assert store.audit_for(f"user:{uid}")[-1]["action"] == "user_purge"
