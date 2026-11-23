"""Testseite: Status, Einmal-Ticket, Cookie, Prüfung für nginx (ziele/projekt-testumgebung.md §4, T3; Etappe E1a).

testuser = role 'user', admin = role 'admin' (conftest). Projekte entstehen über die echte API.
"""
from __future__ import annotations

import time

import pytest

from hydrahive.projects import preview_auth

COOKIE = preview_auth.COOKIE


@pytest.fixture(autouse=True)
def _clean():
    preview_auth.clear()
    from hydrahive.api.middleware import inbound_ratelimit
    if hasattr(inbound_ratelimit, "_hits"):
        inbound_ratelimit._hits.clear()
    yield
    preview_auth.clear()


def _project(client, admin_headers, members=None) -> str:
    body = {"name": "Testseite", "llm_model": "test/model", "members": members or []}
    r = client.post("/api/projects", headers=admin_headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _member(client, admin_headers, role="read") -> str:
    return _project(client, admin_headers, members=[{"username": "testuser", "role": role}])


def _login(client, headers, pid) -> str:
    """Ticket holen, einlösen, Cookie zurückgeben."""
    r = client.post(f"/api/projects/{pid}/preview/open", headers=headers)
    assert r.status_code == 200, r.text
    r = client.get("/api/project-preview/login", params={"t": r.json()["ticket"]}, follow_redirects=False)
    assert r.status_code == 303, r.text
    return r.cookies[COOKIE]


def _check(client, cookie, pid):
    client.cookies.clear()
    return client.get("/api/project-preview/auth", headers={"X-Preview-Project": pid},
                      cookies={COOKIE: cookie} if cookie else None)


# --- Status und Ticket: nur mit Leserecht ---------------------------------------------------------------

def test_status_liefert_port_und_running(client, admin_headers, auth_headers):
    pid = _member(client, admin_headers)
    r = client.get(f"/api/projects/{pid}/preview", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["port"], int) and body["running"] in (True, False)
    assert client.get(f"/api/projects/{pid}/preview", headers=auth_headers).json()["port"] == body["port"]


def test_status_ohne_mitgliedschaft_403(client, admin_headers, auth_headers):
    pid = _project(client, admin_headers)
    assert client.get(f"/api/projects/{pid}/preview", headers=auth_headers).status_code == 403
    assert client.post(f"/api/projects/{pid}/preview/open", headers=auth_headers).status_code == 403


def test_status_ohne_login_401(client, admin_headers):
    pid = _project(client, admin_headers)
    assert client.get(f"/api/projects/{pid}/preview").status_code == 401
    assert client.post(f"/api/projects/{pid}/preview/open").status_code == 401


def test_unbekanntes_projekt_404(client, auth_headers):
    assert client.get("/api/projects/gibt-es-nicht/preview", headers=auth_headers).status_code == 404


# --- T3: Durchreiche ---------------------------------------------------------------------------------------

def test_ohne_cookie_401(client, admin_headers):
    pid = _project(client, admin_headers)
    assert _check(client, None, pid).status_code == 401


def test_mit_cookie_200_und_port(client, admin_headers, auth_headers):
    pid = _member(client, admin_headers)
    port = client.get(f"/api/projects/{pid}/preview", headers=auth_headers).json()["port"]
    cookie = _login(client, auth_headers, pid)
    r = _check(client, cookie, pid)
    assert r.status_code == 200 and r.headers["X-Preview-Port"] == str(port)


def test_cookie_von_x_oeffnet_y_nicht(client, admin_headers, auth_headers):
    x, y = _member(client, admin_headers), _member(client, admin_headers)
    cookie_x = _login(client, auth_headers, x)
    assert _check(client, cookie_x, y).status_code == 403
    r = client.get("/api/project-preview/auth", cookies={COOKIE: cookie_x})       # ohne Projekt-Angabe
    assert r.status_code == 403


def test_cookie_ist_httponly_und_secure(client, admin_headers, auth_headers):
    pid = _member(client, admin_headers)
    r = client.post(f"/api/projects/{pid}/preview/open", headers=auth_headers)
    r = client.get("/api/project-preview/login", params={"t": r.json()["ticket"]}, follow_redirects=False)
    header = r.headers["set-cookie"].lower()
    assert "httponly" in header and "secure" in header


def test_ticket_nur_einmal(client, admin_headers, auth_headers):
    pid = _member(client, admin_headers)
    ticket = client.post(f"/api/projects/{pid}/preview/open", headers=auth_headers).json()["ticket"]
    assert client.get("/api/project-preview/login", params={"t": ticket}, follow_redirects=False).status_code == 303
    assert client.get("/api/project-preview/login", params={"t": ticket}, follow_redirects=False).status_code == 401


def test_abgelaufenes_ticket_abgelehnt(client, admin_headers, auth_headers, monkeypatch):
    pid = _member(client, admin_headers)
    ticket = client.post(f"/api/projects/{pid}/preview/open", headers=auth_headers).json()["ticket"]
    real = time.time
    monkeypatch.setattr(preview_auth.time, "time", lambda: real() + preview_auth.TICKET_TTL + 1)
    assert client.get("/api/project-preview/login", params={"t": ticket}, follow_redirects=False).status_code == 401


def test_gefaelschtes_ticket_abgelehnt(client):
    assert client.get("/api/project-preview/login", params={"t": "erfunden"}, follow_redirects=False).status_code == 401


def test_gefaelschtes_cookie_abgelehnt(client, admin_headers, auth_headers):
    x, y = _member(client, admin_headers), _member(client, admin_headers)
    body, sig = _login(client, auth_headers, x).split(".")
    other_body = preview_auth.issue_cookie("u", y).split(".")[0]
    assert _check(client, f"{other_body}.{sig}", y).status_code == 401      # fremder Inhalt, alte Signatur
    assert _check(client, f"{body}.AAAA", x).status_code == 401


def test_abgelaufenes_cookie_abgelehnt(client, admin_headers, auth_headers, monkeypatch):
    pid = _member(client, admin_headers)
    cookie = _login(client, auth_headers, pid)
    real = time.time
    monkeypatch.setattr(preview_auth.time, "time", lambda: real() + preview_auth.MAX_AGE + 1)
    assert _check(client, cookie, pid).status_code == 401


def test_entzogene_mitgliedschaft_sperrt_sofort(client, admin_headers, auth_headers):
    pid = _member(client, admin_headers)
    cookie = _login(client, auth_headers, pid)
    r = client.patch(f"/api/projects/{pid}", headers=admin_headers, json={"members": []})
    assert r.status_code == 200, r.text
    assert _check(client, cookie, pid).status_code == 401


def test_ticket_eines_nicht_mitglieds_wird_beim_einloesen_abgelehnt(client, admin_headers, auth_headers):
    pid = _member(client, admin_headers)
    ticket = client.post(f"/api/projects/{pid}/preview/open", headers=auth_headers).json()["ticket"]
    client.patch(f"/api/projects/{pid}", headers=admin_headers, json={"members": []})
    assert client.get("/api/project-preview/login", params={"t": ticket}, follow_redirects=False).status_code == 401


# --- T3: Cookie öffnet keine HydraHive-API -------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/api/projects", "/api/auth/me", "/api/sessions"])
def test_cookie_oeffnet_keine_api(client, admin_headers, auth_headers, path):
    pid = _member(client, admin_headers)
    cookie = _login(client, auth_headers, pid)
    client.cookies.clear()
    assert client.get(path, cookies={COOKIE: cookie}).status_code == 401
    assert client.get(path, headers={"Authorization": f"Bearer {cookie}"}).status_code == 401
    assert client.get(f"/api/projects/{pid}/preview", cookies={COOKIE: cookie}).status_code == 401


def test_cookie_schluessel_ist_zweckgebunden():
    from hydrahive.settings import settings
    assert preview_auth._key() != settings.secret_key.encode()
