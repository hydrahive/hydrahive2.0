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
