"""Auth prüft den AKTUELLEN Nutzer, nicht die Rolle im Token (Task a9706460).

Befund 29.09.2026: require_auth/require_admin (360+ Stellen) vertrauten der
Rolle, die beim Login ins JWT (24 h gültig) bzw. in den API-Key-Eintrag
geschrieben wurde. Folgen:
- herabgestufter Admin bleibt bis zu 24 h Admin
- gelöschter Nutzer: Tokens und API-Keys funktionieren weiter
- neu angelegter Nutzer mit gleichem Namen erbt alte Tokens

Regeln (Variante B, Till OK):
- JWT braucht uid, der Nutzer muss existieren und gleich heißen.
  Rolle kommt aus users.json.
- API-Key: Rolle im Key muss der aktuellen entsprechen. Alte Keys ohne
  user_id werden beim ersten Einsatz an den Nutzer gebunden.
- Sonderrolle projektx (Föderations-Client) ist nie Admin.
- Beim Löschen eines Nutzers werden seine API-Keys mitgelöscht.
"""
from __future__ import annotations

import json

import pytest

from hydrahive.api.middleware import api_keys, users
from hydrahive.api.middleware.auth import create_token

ADMIN_ROUTE = "/api/users"          # require_admin
AUTH_ROUTE = "/api/auth/me"         # require_auth


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def made_users(client):
    """Legt Nutzer über den echten Store an und räumt sie wieder weg."""
    created: list[str] = []

    def make(name: str, role: str = "user") -> str:
        uid = users.create(name, "pw-12345678", role)
        created.append(name)
        return uid

    yield make
    for name in created:
        users.delete(name)


def _token(name: str) -> str:
    u = users.get_by_username(name)
    return create_token(name, u["role"], u["user_id"])


# --- JWT -------------------------------------------------------------------

def test_demoted_admin_loses_admin_immediately(client, made_users):
    made_users("ex_admin", "admin")
    token = _token("ex_admin")
    assert client.get(ADMIN_ROUTE, headers=_h(token)).status_code == 200
    users.update_role("ex_admin", "user")
    r = client.get(ADMIN_ROUTE, headers=_h(token))
    assert r.status_code == 403, r.text


def test_promoted_user_gets_current_role(client, made_users):
    made_users("new_admin", "user")
    token = _token("new_admin")
    users.update_role("new_admin", "admin")
    me = client.get(AUTH_ROUTE, headers=_h(token)).json()
    assert me["role"] == "admin"


def test_deleted_user_token_is_rejected(client, made_users):
    made_users("gone_user", "admin")
    token = _token("gone_user")
    users.delete("gone_user")
    assert client.get(AUTH_ROUTE, headers=_h(token)).status_code == 401
    assert client.get(ADMIN_ROUTE, headers=_h(token)).status_code == 401


def test_recreated_namesake_does_not_inherit_old_token(client, made_users):
    made_users("namesake", "admin")
    old = _token("namesake")
    users.delete("namesake")
    made_users("namesake", "user")
    assert client.get(AUTH_ROUTE, headers=_h(old)).status_code == 401


def test_jwt_with_foreign_name_for_uid_is_rejected(client, made_users):
    """uid und Name gehören zusammen: fremder Name zur echten uid → 401."""
    uid = made_users("real_name", "user")
    made_users("other_admin", "admin")
    forged = create_token("other_admin", "admin", uid)
    assert client.get(AUTH_ROUTE, headers=_h(forged)).status_code == 401


def test_jwt_without_uid_is_rejected(client, made_users):
    made_users("legacy_jwt", "admin")
    legacy = create_token("legacy_jwt", "admin")
    assert client.get(ADMIN_ROUTE, headers=_h(legacy)).status_code == 401


def test_optional_auth_uses_current_role(client, made_users):
    from fastapi.security import HTTPAuthorizationCredentials

    from hydrahive.api.middleware.auth import get_current_user_optional
    made_users("opt_user", "admin")
    token = _token("opt_user")
    users.update_role("opt_user", "user")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    assert get_current_user_optional(creds) == ("opt_user", "user")
    users.delete("opt_user")
    assert get_current_user_optional(creds) is None


# --- API-Keys --------------------------------------------------------------

def _legacy_key(name: str, role: str) -> tuple[str, str]:
    """Key wie im Mai angelegt: ohne user_id im Eintrag.

    api_keys.create() trägt die ID selbst nach, darum hier hinterher entfernen.
    """
    plain = api_keys.create(name=f"{name}-hook", username=name, role=role, user_id=None)
    key_id = plain[len(api_keys.PREFIX): len(api_keys.PREFIX) + api_keys._KEY_ID_HEX_LEN]
    data = api_keys._load()
    data[key_id]["user_id"] = None
    api_keys._save(data)
    return plain, key_id


def test_legacy_key_without_uid_keeps_working_and_gets_bound(client, made_users):
    uid = made_users("hook_user", "user")
    plain, key_id = _legacy_key("hook_user", "user")
    assert client.get(AUTH_ROUTE, headers=_h(plain)).status_code == 200
    assert api_keys._load()[key_id]["user_id"] == uid


def test_legacy_key_is_dead_for_recreated_namesake(client, made_users):
    made_users("key_namesake", "user")
    plain, _ = _legacy_key("key_namesake", "user")
    assert client.get(AUTH_ROUTE, headers=_h(plain)).status_code == 200   # bindet
    users.delete("key_namesake")
    made_users("key_namesake", "user")
    assert client.get(AUTH_ROUTE, headers=_h(plain)).status_code == 401


def test_admin_key_after_demotion_is_rejected(client, made_users):
    uid = made_users("key_demoted", "admin")
    plain = api_keys.create(name="k", username="key_demoted", role="admin", user_id=uid)
    assert client.get(ADMIN_ROUTE, headers=_h(plain)).status_code == 200
    users.update_role("key_demoted", "user")
    assert client.get(ADMIN_ROUTE, headers=_h(plain)).status_code == 401
    assert client.get(AUTH_ROUTE, headers=_h(plain)).status_code == 401


def test_deleting_user_deletes_their_api_keys(client, admin_headers, made_users):
    uid = made_users("key_owner", "user")
    api_keys.create(name="k1", username="key_owner", role="user", user_id=uid)
    _legacy_key("key_owner", "user")
    r = client.delete("/api/users/key_owner", headers=admin_headers)
    assert r.status_code == 204, r.text
    assert api_keys.list_keys("key_owner") == []


def test_projektx_key_is_never_admin(client):
    plain = api_keys.create(name="px", username="admin", role="projektx")
    assert client.get(ADMIN_ROUTE, headers=_h(plain)).status_code == 403
    me = client.get(AUTH_ROUTE, headers=_h(plain))
    assert me.status_code == 200 and me.json()["role"] == "projektx"


def test_projektx_key_does_not_act_as_its_registered_owner(client):
    """Der Client-Generator trägt username=admin ein. Bei Besitzprüfungen über
    den Namen darf der Service-Key trotzdem nicht als 'admin' gelten."""
    from hydrahive.db import sessions as sessions_db
    plain = api_keys.create(name="px3", username="admin", role="projektx")
    me = client.get(AUTH_ROUTE, headers=_h(plain)).json()
    assert me["username"] != "admin"
    s = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="nur admin")
    try:
        r = client.get(f"/api/sessions/{s.id}", headers=_h(plain))
        assert r.status_code == 403, r.text
    finally:
        sessions_db.delete(s.id)


def test_legacy_user_key_binding_skips_service_keys(client, made_users):
    """Die Bindung alter Keys fasst Service-Keys (projektx) des Nutzers nicht an."""
    uid = made_users("mixed_owner", "user")
    user_plain, user_kid = _legacy_key("mixed_owner", "user")
    _svc_plain, svc_kid = _legacy_key("mixed_owner", "projektx")
    assert client.get(AUTH_ROUTE, headers=_h(user_plain)).status_code == 200
    data = api_keys._load()
    assert data[user_kid]["user_id"] == uid
    assert not data[svc_kid].get("user_id")


def test_projektx_key_is_not_a_principal(client):
    """Neue benutzereigene Routen (require_principal) lehnen Service-Keys ab."""
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    from hydrahive.api.middleware.auth import require_principal
    plain = api_keys.create(name="px2", username="admin", role="projektx")
    with pytest.raises(HTTPException) as exc:
        require_principal(HTTPAuthorizationCredentials(scheme="Bearer", credentials=plain))
    assert exc.value.status_code == 401


# --- Sonderwege: ?token= und Container-Konsole ----------------------------

def test_files_query_token_of_deleted_user_is_rejected(client, made_users):
    made_users("file_user", "user")
    token = _token("file_user")
    users.delete("file_user")
    r = client.get("/api/files", params={"path": "/etc/hostname", "token": token})
    assert r.status_code == 401


def test_container_console_uses_current_role(client, made_users):
    from hydrahive.api.routes import container_console
    made_users("console_user", "admin")
    token = _token("console_user")
    users.update_role("console_user", "user")
    assert container_console._authenticate(token) == ("console_user", "user")
    users.delete("console_user")
    assert container_console._authenticate(token) is None


def test_api_keys_file_stays_valid_json(client, made_users):
    made_users("json_user", "user")
    _legacy_key("json_user", "user")
    json.loads(api_keys._path().read_text())
