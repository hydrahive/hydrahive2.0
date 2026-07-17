"""Regressionstests für die Auth-Middleware.

Getestet: create_token, _decode, require_auth, require_admin,
get_current_user_optional — ohne Netzwerk, ohne DB.
"""
from __future__ import annotations

from datetime import datetime, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from hydrahive.api.middleware.auth import (
    _decode,
    create_token,
    get_current_user_optional,
    require_admin,
    require_auth,
    require_principal,
)
from hydrahive.settings import settings

TEST_SECRET = "test-geheimnis-fuer-unit-tests"


@pytest.fixture(autouse=True)
def secret_patch(monkeypatch):
    """Überschreibt settings.secret_key für jeden Test mit einem festen Wert.

    cached_property speichert den Wert im __dict__ der Instanz —
    wir löschen den Cache-Eintrag und setzen ihn direkt neu.
    """
    settings.__dict__.pop("secret_key", None)
    monkeypatch.setitem(settings.__dict__, "secret_key", TEST_SECRET)
    yield
    settings.__dict__.pop("secret_key", None)


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# ---------------------------------------------------------------------------
# _decode
# ---------------------------------------------------------------------------

def test_gueltiges_token_dekodiert_korrekt():
    token = create_token("alice", "user")
    payload = _decode(token)
    assert payload["sub"] == "alice"
    assert payload["role"] == "user"
    assert "exp" in payload


def test_neues_token_enthaelt_stabile_user_id():
    token = create_token("alice", "user", "stable-123")
    assert _decode(token)["uid"] == "stable-123"


def test_falscher_secret_wirft_401():
    fremdes_token = jwt.encode(
        {"sub": "eve", "role": "user"},
        "falsches-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        _decode(fremdes_token)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "invalid_token"


def test_abgelaufenes_token_wirft_401_token_expired():
    abgelaufen = jwt.encode(
        {
            "sub": "bob",
            "role": "user",
            "exp": datetime(2020, 1, 1, tzinfo=timezone.utc),
        },
        TEST_SECRET,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        _decode(abgelaufen)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "token_expired"


# ---------------------------------------------------------------------------
# require_auth
# ---------------------------------------------------------------------------

def test_require_auth_ohne_credentials_wirft_401():
    with pytest.raises(HTTPException) as exc_info:
        require_auth(None)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "not_authenticated"


def test_require_auth_mit_gueltigem_token_gibt_username_und_rolle():
    token = create_token("clara", "editor")
    username, role = require_auth(_creds(token))
    assert username == "clara"
    assert role == "editor"


# ---------------------------------------------------------------------------
# require_principal
# ---------------------------------------------------------------------------


def test_require_principal_nutzt_stabile_id_und_aktuelle_rolle(monkeypatch):
    from hydrahive.api.middleware import users

    monkeypatch.setattr(
        users,
        "get_by_id",
        lambda user_id: {
            "user_id": user_id,
            "username": "clara",
            "role": "admin",
        },
    )
    token = create_token("clara", "user", "stable-123")

    principal = require_principal(_creds(token))

    assert principal.user_id == "stable-123"
    assert principal.username == "clara"
    assert principal.role == "admin"


def test_require_principal_lehnt_legacy_token_ohne_user_id_ab():
    token = create_token("clara", "user")

    with pytest.raises(HTTPException) as exc_info:
        require_principal(_creds(token))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "invalid_token"


def test_require_principal_lehnt_geloeschten_user_ab(monkeypatch):
    from hydrahive.api.middleware import users

    monkeypatch.setattr(users, "get_by_id", lambda _user_id: None)
    token = create_token("clara", "user", "deleted-123")

    with pytest.raises(HTTPException) as exc_info:
        require_principal(_creds(token))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "invalid_token"


def test_require_principal_lehnt_neuangelegten_user_mit_gleichem_namen_ab(monkeypatch):
    from hydrahive.api.middleware import users

    monkeypatch.setattr(users, "get_by_id", lambda _user_id: None)
    old_token = create_token("clara", "user", "old-user-id")

    with pytest.raises(HTTPException) as exc_info:
        require_principal(_creds(old_token))

    assert exc_info.value.status_code == 401


def test_require_principal_akzeptiert_id_gebundenen_api_key(monkeypatch):
    from hydrahive.api.middleware import api_keys, users

    monkeypatch.setattr(
        api_keys,
        "verify",
        lambda _token: {"user_id": "stable-123", "username": "clara", "role": "user"},
    )
    monkeypatch.setattr(
        users,
        "get_by_id",
        lambda user_id: {"user_id": user_id, "username": "clara", "role": "user"},
    )

    principal = require_principal(_creds("hhk_test"))

    assert principal.user_id == "stable-123"


def test_require_principal_lehnt_api_key_nach_rollenaenderung_ab(monkeypatch):
    from hydrahive.api.middleware import api_keys, users

    monkeypatch.setattr(
        api_keys,
        "verify",
        lambda _token: {"user_id": "stable-123", "username": "clara", "role": "admin"},
    )
    monkeypatch.setattr(
        users,
        "get_by_id",
        lambda user_id: {"user_id": user_id, "username": "clara", "role": "user"},
    )

    with pytest.raises(HTTPException) as exc_info:
        require_principal(_creds("hhk_test"))

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# require_admin
# ---------------------------------------------------------------------------

def test_require_admin_mit_user_rolle_wirft_403():
    with pytest.raises(HTTPException) as exc_info:
        require_admin(("dave", "user"))
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "admin_only"


def test_require_admin_mit_admin_rolle_gibt_username_und_rolle():
    result = require_admin(("eva", "admin"))
    assert result == ("eva", "admin")


# ---------------------------------------------------------------------------
# get_current_user_optional
# ---------------------------------------------------------------------------

def test_optional_ohne_credentials_gibt_none():
    result = get_current_user_optional(None)
    assert result is None


def test_optional_mit_ungueltigem_token_gibt_none():
    result = get_current_user_optional(_creds("das-ist-kein-jwt"))
    assert result is None


def test_optional_mit_gueltigem_token_gibt_username_und_rolle():
    token = create_token("frank", "admin")
    result = get_current_user_optional(_creds(token))
    assert result == ("frank", "admin")
