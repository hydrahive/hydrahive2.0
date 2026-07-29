"""End-to-End: Member-Rollen-Enforcement über die Projekt-Routen.

Nutzt echte Projekt-Persistenz (kein Mock) — deckt Migration, Rollen-Setzen
und Enforcement ab. testuser = role 'user', admin = role 'admin'.
"""
from __future__ import annotations

import pytest


def _create_project(client, admin_headers, members=None) -> str:
    body = {"name": "Rollen-Projekt", "llm_model": "test/model"}
    if members is not None:
        body["members"] = members
    r = client.post("/api/projects", headers=admin_headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestMemberRolePersistence:
    def test_create_normalizes_legacy_str_members(self, client, admin_headers):
        pid = _create_project(client, admin_headers, members=["testuser"])
        r = client.get(f"/api/projects/{pid}", headers=admin_headers)
        assert r.json()["members"] == [{"username": "testuser", "role": "write"}]

    def test_add_member_with_role(self, client, admin_headers):
        pid = _create_project(client, admin_headers)
        r = client.post(f"/api/projects/{pid}/members/testuser",
                        headers=admin_headers, json={"role": "read"})
        assert r.status_code == 200
        assert {"username": "testuser", "role": "read"} in r.json()["members"]

    def test_add_member_default_role_write(self, client, admin_headers):
        pid = _create_project(client, admin_headers)
        r = client.post(f"/api/projects/{pid}/members/testuser", headers=admin_headers)
        assert r.status_code == 200
        assert {"username": "testuser", "role": "write"} in r.json()["members"]

    def test_set_member_role(self, client, admin_headers):
        pid = _create_project(client, admin_headers, members=["testuser"])
        r = client.patch(f"/api/projects/{pid}/members/testuser",
                         headers=admin_headers, json={"role": "admin"})
        assert r.status_code == 200
        assert {"username": "testuser", "role": "admin"} in r.json()["members"]

    def test_set_role_unknown_member_404(self, client, admin_headers):
        pid = _create_project(client, admin_headers)
        r = client.patch(f"/api/projects/{pid}/members/ghost",
                         headers=admin_headers, json={"role": "read"})
        assert r.status_code == 404

    def test_invalid_role_rejected(self, client, admin_headers):
        pid = _create_project(client, admin_headers)
        r = client.post(f"/api/projects/{pid}/members/testuser",
                        headers=admin_headers, json={"role": "superuser"})
        assert r.status_code == 422  # pydantic pattern


class TestMemberManagementAuth:
    def test_project_admin_member_can_manage(self, client, admin_headers, auth_headers):
        # testuser als Projekt-admin -> darf weitere Members hinzufügen.
        pid = _create_project(client, admin_headers,
                              members=[{"username": "testuser", "role": "admin"}])
        r = client.post(f"/api/projects/{pid}/members/admin",
                        headers=auth_headers, json={"role": "read"})
        assert r.status_code == 200

    def test_write_member_cannot_manage(self, client, admin_headers, auth_headers):
        pid = _create_project(client, admin_headers,
                              members=[{"username": "testuser", "role": "write"}])
        r = client.post(f"/api/projects/{pid}/members/admin",
                        headers=auth_headers, json={"role": "read"})
        assert r.status_code == 403

    def test_read_member_cannot_manage(self, client, admin_headers, auth_headers):
        pid = _create_project(client, admin_headers,
                              members=[{"username": "testuser", "role": "read"}])
        r = client.post(f"/api/projects/{pid}/members/admin", headers=auth_headers)
        assert r.status_code == 403

    def test_non_member_cannot_manage(self, client, admin_headers, auth_headers):
        pid = _create_project(client, admin_headers)
        r = client.post(f"/api/projects/{pid}/members/admin", headers=auth_headers)
        assert r.status_code == 403


class TestReadVsWriteEnforcement:
    def test_read_member_can_view_project(self, client, admin_headers, auth_headers):
        pid = _create_project(client, admin_headers,
                              members=[{"username": "testuser", "role": "read"}])
        r = client.get(f"/api/projects/{pid}", headers=auth_headers)
        assert r.status_code == 200

    def test_non_member_cannot_view_project(self, client, admin_headers, auth_headers):
        pid = _create_project(client, admin_headers)
        r = client.get(f"/api/projects/{pid}", headers=auth_headers)
        assert r.status_code == 403
