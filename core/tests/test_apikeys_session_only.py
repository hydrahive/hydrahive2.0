"""API-Keys verwalten nur mit Login-Sitzung (Task 9e9439ff).

Befund 30.09.2026 live: Ein API-Key konnte selbst weitere API-Keys anlegen
(POST /api/auth/apikeys mit hhk_… → 201). Keys laufen nicht ab. Ein
abgegriffener Key hätte sich so dauerhafte Ersatz-Keys erzeugen können, auch
ein Agent über ein Credential-Profil (fetch_url setzt den Key ein).
Jetzt: Anlegen und Löschen nur mit JWT, Lesen der eigenen Liste auch mit Key.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _own_keys_file(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "api_keys_config", tmp_path / "api_keys.json", raising=False)


def _key(client, headers, name="k1") -> str:
    r = client.post("/api/auth/apikeys", json={"name": name}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["key"]


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_login_session_can_create_and_delete(client, auth_headers):
    _key(client, auth_headers)
    keys = client.get("/api/auth/apikeys", headers=auth_headers).json()
    assert [k["name"] for k in keys] == ["k1"]
    assert client.delete(f"/api/auth/apikeys/{keys[0]['id']}", headers=auth_headers).status_code == 204


def test_api_key_cannot_create_api_key(client, auth_headers):
    key = _key(client, auth_headers)
    r = client.post("/api/auth/apikeys", json={"name": "kette"}, headers=_bearer(key))
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "session_required"
    names = [k["name"] for k in client.get("/api/auth/apikeys", headers=auth_headers).json()]
    assert names == ["k1"]


def test_api_key_cannot_delete_api_key(client, auth_headers):
    key = _key(client, auth_headers)
    other = _key(client, auth_headers, name="k2")
    keys = client.get("/api/auth/apikeys", headers=auth_headers).json()
    target = next(k for k in keys if k["name"] == "k2")
    r = client.delete(f"/api/auth/apikeys/{target['id']}", headers=_bearer(key))
    assert r.status_code == 403
    assert len(client.get("/api/auth/apikeys", headers=auth_headers).json()) == 2
    assert other  # nur benutzt, damit der Key sicher existiert


def test_api_key_can_still_list_own_keys(client, auth_headers):
    key = _key(client, auth_headers)
    r = client.get("/api/auth/apikeys", headers=_bearer(key))
    assert r.status_code == 200
    assert [k["name"] for k in r.json()] == ["k1"]
    assert all("key" not in k and "key_hash" not in k for k in r.json())


def test_api_key_still_works_for_normal_api(client, auth_headers):
    key = _key(client, auth_headers)
    assert client.get("/api/sessions", headers=_bearer(key)).status_code == 200


def test_user_sees_only_own_keys(client, auth_headers, admin_headers):
    _key(client, auth_headers, name="nutzer-key")
    _key(client, admin_headers, name="admin-key")
    names = [k["name"] for k in client.get("/api/auth/apikeys", headers=auth_headers).json()]
    assert names == ["nutzer-key"]


def test_user_cannot_delete_foreign_key(client, auth_headers, admin_headers):
    _key(client, admin_headers, name="admin-key")
    admin_key = next(k for k in client.get("/api/auth/apikeys", headers=admin_headers).json() if k["name"] == "admin-key")
    r = client.delete(f"/api/auth/apikeys/{admin_key['id']}", headers=auth_headers)
    assert r.status_code == 404


def test_mine_parameter_shows_only_own_keys_even_for_admin(client, auth_headers, admin_headers):
    """Profilseite „Meine API-Keys“: auch ein Admin sieht dort nur die eigenen Keys."""
    _key(client, auth_headers, name="nutzer-key")
    _key(client, admin_headers, name="admin-key")
    all_for_admin = [k["name"] for k in client.get("/api/auth/apikeys", headers=admin_headers).json()]
    assert sorted(all_for_admin) == ["admin-key", "nutzer-key"]
    mine = [k["name"] for k in client.get("/api/auth/apikeys?mine=true", headers=admin_headers).json()]
    assert mine == ["admin-key"]
    assert [k["name"] for k in client.get("/api/auth/apikeys?mine=true", headers=auth_headers).json()] == ["nutzer-key"]
