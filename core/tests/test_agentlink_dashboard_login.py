"""AgentLink-Dashboard nur für Admins mit HydraHive-Login (Task 3bd963b2, b2).

nginx gab /agentlink/, /agentlink/api/ und /agentlink/ws ohne Login ins LAN.
Jetzt prüft nginx per auth_request ein kurzlebiges Cookie, das HydraHive nur
Admins beim Klick auf „Dashboard öffnen“ ausstellt.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from hydrahive.api.middleware import users
from hydrahive.api.middleware.auth import create_token

SESSION = "/api/agentlink/dashboard-session"
CHECK = "/api/agentlink/dashboard-auth"
COOKIE = "hh_agentlink"
ROOT = Path(__file__).resolve().parents[2]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def made_users(client):
    created: list[str] = []

    def make(name: str, role: str) -> str:
        created.append(name)
        uid = users.create(name, "pw-12345678", role)
        return create_token(name, role, uid)

    yield make
    for name in created:
        users.delete(name)


def _open(client, token: str):
    return client.post(SESSION, headers=_h(token))


def _check(client, cookie: str | None):
    client.cookies.clear()
    headers = {"Cookie": f"{COOKIE}={cookie}"} if cookie is not None else {}
    return client.get(CHECK, headers=headers)


# --- Ausstellen -----------------------------------------------------------

def test_admin_gets_scoped_httponly_cookie(client, made_users):
    r = _open(client, made_users("dash_admin", "admin"))
    assert r.status_code == 200, r.text
    assert r.json()["url"] == "/agentlink/"
    raw = r.headers["set-cookie"].lower()
    assert f"{COOKIE}=" in raw
    for attr in ("httponly", "secure", "samesite=strict", "path=/agentlink/", "max-age="):
        assert attr in raw, attr


def test_non_admin_gets_no_cookie(client, made_users):
    r = _open(client, made_users("dash_user", "user"))
    assert r.status_code == 403
    assert "set-cookie" not in r.headers


def test_session_needs_login(client):
    assert client.post(SESSION).status_code == 401


# --- Prüfen (nginx auth_request) -----------------------------------------

def _cookie_for(client, token: str) -> str:
    return _open(client, token).cookies[COOKIE]


def test_valid_cookie_passes(client, made_users):
    c = _cookie_for(client, made_users("chk_admin", "admin"))
    assert _check(client, c).status_code == 204


@pytest.mark.parametrize("cookie", [None, "", "quatsch", "a.b", "x" * 300])
def test_missing_or_garbage_cookie_fails(client, cookie):
    assert _check(client, cookie).status_code == 401


def test_tampered_cookie_fails(client, made_users):
    c = _cookie_for(client, made_users("tamper_admin", "admin"))
    body, _, sig = c.rpartition(".")
    flipped = sig[:-1] + ("A" if sig[-1] != "A" else "B")
    assert _check(client, f"{body}.{flipped}").status_code == 401


def test_expired_cookie_fails(client, made_users, monkeypatch):
    from hydrahive.api.routes import _agentlink_dashboard as dash
    c = _cookie_for(client, made_users("old_admin", "admin"))
    real = time.time
    monkeypatch.setattr(dash.time, "time", lambda: real() + dash.MAX_AGE + 5)
    assert _check(client, c).status_code == 401


def test_demoted_admin_loses_dashboard(client, made_users):
    c = _cookie_for(client, made_users("demoted_admin", "admin"))
    users.update_role("demoted_admin", "user")
    assert _check(client, c).status_code == 401


def test_deleted_admin_loses_dashboard(client, made_users):
    c = _cookie_for(client, made_users("gone_admin", "admin"))
    users.delete("gone_admin")
    assert _check(client, c).status_code == 401


def test_login_jwt_is_not_accepted_as_cookie(client, made_users):
    """Das Cookie ist ein eigener Schein, kein Login-Token."""
    token = made_users("jwt_admin", "admin")
    assert _check(client, token).status_code == 401


def test_cookie_key_is_separate_from_other_signatures(client):
    """Zweckgebundener Schlüssel: nicht der rohe secret_key (Login-JWTs) und
    nicht der AgentLink-State-Schlüssel. Ein Leck an einer Stelle öffnet
    nicht die andere."""
    from hydrahive.agentlink import signing
    from hydrahive.api.routes import _agentlink_dashboard as dash
    from hydrahive.settings import settings
    assert dash._key() != settings.secret_key.encode()
    assert dash._key() != signing._key()
    assert len(dash._key()) == 32


def test_cookie_is_not_a_login(client, made_users):
    """Umgekehrt: Der Dashboard-Schein öffnet keine HydraHive-API."""
    c = _cookie_for(client, made_users("scope_admin", "admin"))
    assert client.get("/api/users", headers=_h(c)).status_code == 401


# --- nginx-Installer ------------------------------------------------------

def _agentlink_blocks() -> str:
    conf = (ROOT / "installer/modules/60-nginx.sh").read_text()
    return conf[conf.index("location /agentlink/ {"):]


@pytest.mark.parametrize("loc", ["location /agentlink/ {", "location /agentlink/api/ {",
                                 "location /agentlink/ws {"])
def test_every_agentlink_location_requires_auth(loc):
    blocks = _agentlink_blocks()
    start = blocks.index(loc)
    end = blocks.index("}", start)
    assert "auth_request /_hh_agentlink_auth;" in blocks[start:end], loc


def test_auth_location_is_internal_and_points_to_core():
    conf = (ROOT / "installer/modules/60-nginx.sh").read_text()
    start = conf.index("location = /_hh_agentlink_auth {")
    block = conf[start:conf.index("}", start)]
    assert "internal;" in block
    assert "/api/agentlink/dashboard-auth" in block
    assert "proxy_pass_request_body off;" in block


def test_updater_rewrites_nginx_without_the_marker():
    updater = (ROOT / "installer/update.sh").read_text()
    assert 'grep -q "hh_agentlink_auth"' in updater
