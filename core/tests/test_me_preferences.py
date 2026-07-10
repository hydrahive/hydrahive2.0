from __future__ import annotations


def test_preferences_requires_auth(client):
    r = client.get("/api/me/preferences")
    assert r.status_code == 401


def test_preferences_default(client, auth_headers):
    r = client.get("/api/me/preferences", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {
        "active_project_id": None,
        "active_media_project_id": None,
        "active_vault_scope": "private",
        "cockpit_layout": {},
    }


def test_preferences_patch_persists_per_user(client, auth_headers, admin_headers):
    r = client.patch(
        "/api/me/preferences",
        headers=auth_headers,
        json={"active_vault_scope": "family", "cockpit_layout": {"project": {"rightCollapsed": True}}},
    )
    assert r.status_code == 200
    assert r.json()["active_vault_scope"] == "family"
    assert r.json()["cockpit_layout"] == {"project": {"rightCollapsed": True}}

    again = client.get("/api/me/preferences", headers=auth_headers)
    assert again.status_code == 200
    assert again.json()["active_vault_scope"] == "family"
    assert again.json()["cockpit_layout"] == {"project": {"rightCollapsed": True}}

    admin = client.get("/api/me/preferences", headers=admin_headers)
    assert admin.status_code == 200
    assert admin.json()["active_vault_scope"] == "private"
    assert admin.json()["cockpit_layout"] == {}


def test_preferences_rejects_unknown_fields(client, auth_headers):
    r = client.patch("/api/me/preferences", headers=auth_headers, json={"secret": "nope"})
    assert r.status_code == 422


def test_preferences_rejects_invalid_vault_scope(client, auth_headers):
    r = client.patch("/api/me/preferences", headers=auth_headers, json={"active_vault_scope": "root"})
    assert r.status_code == 422


def test_preferences_unknown_project_is_sanitized(client, auth_headers):
    r = client.patch(
        "/api/me/preferences",
        headers=auth_headers,
        json={"active_project_id": "does-not-exist", "active_media_project_id": "also-missing"},
    )
    assert r.status_code == 200
    assert r.json()["active_project_id"] is None
    assert r.json()["active_media_project_id"] is None
