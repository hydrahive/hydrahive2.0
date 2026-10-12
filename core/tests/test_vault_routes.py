"""Vault-Schnittstellen: Status, PIN festlegen, Entsperren, Sperren, Reset, Admin-Reset (vault.md §4.2–4.4)."""
from __future__ import annotations

import pytest

from tests.conftest import error_code

PW = "testpass123"


@pytest.fixture(autouse=True)
def _ohne_pin(client, admin_headers):
    from hydrahive.vault import lockout, pins
    users = client.get("/api/users", headers=admin_headers).json()
    for u in users:
        pins.reset(u["user_id"])
    lockout.clear()
    yield
    for u in users:
        pins.reset(u["user_id"])
    lockout.clear()


def _setup(client, h, pin="135790"):
    return client.post("/api/vault/setup", json={"password": PW, "pin": pin}, headers=h)


def test_status_ohne_pin(client, auth_headers):
    r = client.get("/api/vault/status", headers=auth_headers)
    assert r.status_code == 200 and r.json() == {"pin_set": False, "unlocked": False, "remaining_seconds": 0,
                                                 "idle_seconds": 900}


def test_setup_nur_mit_richtigem_login_passwort(client, auth_headers):
    r = client.post("/api/vault/setup", json={"password": "falsch", "pin": "135790"}, headers=auth_headers)
    assert r.status_code == 401 and error_code(r) == "invalid_credentials"
    r = _setup(client, auth_headers)
    assert r.status_code == 200 and r.json()["vault_token"]
    assert client.get("/api/vault/status", headers=auth_headers).json()["pin_set"] is True


def test_setup_nicht_ueberschreiben_wenn_pin_schon_gesetzt(client, auth_headers):
    _setup(client, auth_headers)
    r = _setup(client, auth_headers, pin="999999")
    assert r.status_code == 409 and error_code(r) == "vault_pin_exists"


def test_setup_falsches_format(client, auth_headers):
    r = _setup(client, auth_headers, pin="12ab")
    assert r.status_code == 422 and error_code(r) == "vault_pin_format"


def test_unlock_und_status(client, auth_headers):
    _setup(client, auth_headers)
    r = client.post("/api/vault/unlock", json={"pin": "135790"}, headers=auth_headers)
    assert r.status_code == 200
    tok = r.json()["vault_token"]
    s = client.get("/api/vault/status", headers={**auth_headers, "X-HH-Vault": tok}).json()
    assert s["unlocked"] is True and 0 < s["remaining_seconds"] <= 900
    r = client.post("/api/vault/unlock", json={"pin": "000000"}, headers=auth_headers)
    assert r.status_code == 401 and error_code(r) == "vault_pin_wrong"


def test_fuenf_fehlversuche_sperren(client, auth_headers):
    _setup(client, auth_headers)
    for _ in range(5):
        assert client.post("/api/vault/unlock", json={"pin": "000000"}, headers=auth_headers).status_code == 401
    r = client.post("/api/vault/unlock", json={"pin": "135790"}, headers=auth_headers)
    assert r.status_code == 429 and error_code(r) == "vault_too_many_attempts"
    assert int(r.headers["Retry-After"]) > 0


def test_lock_macht_alle_token_ungueltig(client, auth_headers):
    tok = _setup(client, auth_headers).json()["vault_token"]
    assert client.post("/api/vault/lock", headers=auth_headers).status_code == 200
    s = client.get("/api/vault/status", headers={**auth_headers, "X-HH-Vault": tok}).json()
    assert s["unlocked"] is False and s["pin_set"] is True
    assert client.post("/api/vault/unlock", json={"pin": "135790"}, headers=auth_headers).status_code == 200


def test_pin_vergessen_mit_login_passwort(client, auth_headers):
    old = _setup(client, auth_headers).json()["vault_token"]
    r = client.post("/api/vault/reset", json={"password": "falsch", "pin": "246802"}, headers=auth_headers)
    assert r.status_code == 401
    r = client.post("/api/vault/reset", json={"password": PW, "pin": "246802"}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["vault_token"]
    assert client.get("/api/vault/status", headers={**auth_headers, "X-HH-Vault": old}).json()["unlocked"] is False
    assert client.post("/api/vault/unlock", json={"pin": "246802"}, headers=auth_headers).status_code == 200


def test_admin_reset_kennt_die_pin_nie(client, auth_headers, admin_headers):
    _setup(client, auth_headers)
    uid = next(u["user_id"] for u in client.get("/api/users", headers=admin_headers).json()
               if u["username"] == "testuser")
    assert client.post(f"/api/vault/admin/reset/{uid}", headers=auth_headers).status_code == 403
    r = client.post(f"/api/vault/admin/reset/{uid}", headers=admin_headers)
    assert r.status_code == 200 and "pin" not in r.text.lower().replace("pin_set", "")
    assert client.get("/api/vault/status", headers=auth_headers).json()["pin_set"] is False
    assert client.post("/api/vault/admin/reset/unbekannt", headers=admin_headers).status_code == 404


def test_api_key_kann_vault_nicht_einrichten(client, auth_headers):
    key = client.post("/api/auth/apikeys", json={"name": "v"}, headers=auth_headers).json()["key"]
    h = {"Authorization": f"Bearer {key}"}
    assert client.post("/api/vault/setup", json={"password": PW, "pin": "135790"}, headers=h).status_code == 403
    assert client.post("/api/vault/unlock", json={"pin": "135790"}, headers=h).status_code == 403


def test_status_verlaengert_die_entsperrung_nicht(client, auth_headers):
    """Die Kopfleiste fragt /vault/status regelmäßig ab – das darf die 15-min-Sperre NICHT aufschieben."""
    _setup(client, auth_headers)
    tok = client.post("/api/vault/unlock", json={"pin": "135790"}, headers=auth_headers).json()["vault_token"]
    r = client.get("/api/vault/status", headers={**auth_headers, "X-HH-Vault": tok})
    assert r.status_code == 200 and "X-HH-Vault-Refresh" not in r.headers
