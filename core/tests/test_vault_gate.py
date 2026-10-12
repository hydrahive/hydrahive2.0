"""Vault-Sperre an Schnittstellen (docs/specs/vault.md §4.1, §4.3).

Login-Token ohne gültige Entsperrung → 423 vault_locked. API-Keys sind Hintergrund-Zugriff (keine PIN).
<audio>/<img> können keinen Header setzen → Vault-Token auch als ?vault=.
"""
from __future__ import annotations

import time

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from tests.conftest import error_code


def _app() -> FastAPI:
    from hydrahive.vault.gate import require_vault_unlocked
    app = FastAPI()
    r = APIRouter()

    @r.get("/geheim", dependencies=[Depends(require_vault_unlocked)])
    def geheim() -> dict:
        return {"ok": True}

    app.include_router(r)
    return app


def _uid(client, admin_headers, name="testuser") -> str:
    return next(u["user_id"] for u in client.get("/api/users", headers=admin_headers).json() if u["username"] == name)


@pytest.fixture
def pin_user(client, admin_headers):
    from hydrahive.vault import pins
    uid = _uid(client, admin_headers)
    pins.set_pin(uid, "135790")
    yield uid
    pins.reset(uid)


def _token(uid):
    from hydrahive.vault import pins, tokens
    return tokens.issue(uid, generation=pins.generation(uid), now=time.time())


def test_ohne_entsperrung_423(client, auth_headers, pin_user):
    r = TestClient(_app()).get("/geheim", headers=auth_headers)
    assert r.status_code == 423 and error_code(r) == "vault_locked"


def test_ohne_pin_423_mit_hinweis_setup(client, auth_headers, admin_headers):
    from hydrahive.vault import pins
    pins.reset(_uid(client, admin_headers))
    r = TestClient(_app()).get("/geheim", headers=auth_headers)
    assert r.status_code == 423 and r.json()["detail"]["params"]["pin_set"] is False


def test_mit_gueltigem_vault_token_offen_und_verlaengert(client, auth_headers, pin_user):
    tok = _token(pin_user)
    r = TestClient(_app()).get("/geheim", headers={**auth_headers, "X-HH-Vault": tok})
    assert r.status_code == 200
    assert r.headers.get("X-HH-Vault-Refresh"), "gleitende Sperre: neuer Token im Antwort-Header"


def test_vault_token_als_query_fuer_audio_img(client, auth_headers, pin_user):
    r = TestClient(_app()).get("/geheim", params={"vault": _token(pin_user)}, headers=auth_headers)
    assert r.status_code == 200


def test_fremder_vault_token_hilft_nicht(client, auth_headers, admin_headers, pin_user):
    from hydrahive.vault import pins, tokens
    admin_uid = _uid(client, admin_headers, "admin")
    pins.set_pin(admin_uid, "246802")
    try:
        fremd = tokens.issue(admin_uid, generation=pins.generation(admin_uid), now=time.time())
        assert TestClient(_app()).get("/geheim", headers={**auth_headers, "X-HH-Vault": fremd}).status_code == 423
    finally:
        pins.reset(admin_uid)


def test_nach_pin_reset_alter_token_ungueltig(client, auth_headers, pin_user):
    from hydrahive.vault import pins
    tok = _token(pin_user)
    pins.set_pin(pin_user, "111222")
    assert TestClient(_app()).get("/geheim", headers={**auth_headers, "X-HH-Vault": tok}).status_code == 423


def test_api_key_braucht_keine_pin(client, auth_headers, pin_user):
    r = client.post("/api/auth/apikeys", json={"name": "vault-test"}, headers=auth_headers)
    assert r.status_code == 201, r.text
    key = r.json()["key"]
    assert TestClient(_app()).get("/geheim", headers={"Authorization": f"Bearer {key}"}).status_code == 200


def test_ohne_login_401(client):
    assert TestClient(_app()).get("/geheim").status_code == 401
