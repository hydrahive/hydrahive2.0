"""V1 — Schalter shared/remote_edits in GET/PUT /api/federation/catalog/settings
(docs/specs/federation-shared-tasks.md §Schalter). Standard aus, nur Admin.
remote_edits hat noch keine Wirkung (Spec Z. 86-90, Till bestätigt vor G4) —
hier wird nur geprüft, dass der Wert gespeichert und gelesen wird.
"""
from __future__ import annotations

import pytest

from tests._own_rows import only_own_rows

CATALOG_TABLES = (
    "federation_catalog_settings", "federation_catalog_users",
    "federation_catalog_excluded_projects", "federation_catalog_cursors",
)


@pytest.fixture(autouse=True)
def _clean(client, admin_headers):
    with only_own_rows(*CATALOG_TABLES):
        yield


def _settings_body(**over):
    base = {
        "enabled": False,
        "interval_seconds": 300,
        "users": [],
        "excluded_projects": [],
    }
    base.update(over)
    return base


def test_get_settings_defaults_shared_and_remote_edits_off(client, admin_headers):
    r = client.get("/api/federation/catalog/settings", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["shared"] is False
    assert body["remote_edits"] is False


def test_put_settings_sets_shared_and_remote_edits(client, admin_headers):
    r = client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(shared=True, remote_edits=True),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["shared"] is True
    assert body["remote_edits"] is True

    again = client.get("/api/federation/catalog/settings", headers=admin_headers)
    assert again.json()["shared"] is True
    assert again.json()["remote_edits"] is True


def test_put_settings_shared_invalid_type_422(client, admin_headers):
    r = client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(shared="ja"),
    )
    assert r.status_code == 422


def test_put_settings_remote_edits_invalid_type_422(client, admin_headers):
    r = client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(remote_edits="ja"),
    )
    assert r.status_code == 422


def test_get_settings_requires_admin(client, auth_headers):
    r = client.get("/api/federation/catalog/settings", headers=auth_headers)
    assert r.status_code == 403


def test_put_settings_requires_admin(client, auth_headers):
    r = client.put(
        "/api/federation/catalog/settings", headers=auth_headers,
        json=_settings_body(shared=True),
    )
    assert r.status_code == 403
