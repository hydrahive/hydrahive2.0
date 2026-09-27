"""Credentials gehen nur an den Host, für den sie gedacht sind (Security-Task ef27f79b).

Vorher war "*" der UI-Standard: fetch_url setzte das Secret bei JEDER Adresse
ein — per Prompt-Injection also auch bei einer Angreifer-URL. Außerdem wurden
die Credential-Werte des Nutzers nicht aus Tool-Ausgaben geschwärzt.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.credentials.models import Credential, has_concrete_host, matches_url

TOKEN = "tok-" + "x" * 24  # >= MIN_SECRET_LEN


@pytest.mark.parametrize("pattern,expected", [
    ("*", False),
    ("", False),
    ("https://*", False),
    ("*://*/*", False),
    ("https://*.com/*", False),          # Wildcard auf eine ganze TLD
    ("*github.com*", False),             # ohne Schema, Wildcard im Host
    ("https://api.example.com*", False), # Wildcard hängt am Host
    ("https://api*.example.com/*", False),
    ("api.example.com/*", False),        # ohne Schema → nie automatisch
    ("https://*.example.com/*", True),
    ("https://api.example.com/*", True),
    ("https://api.example.com", True),
    ("http://192.168.1.20:8080/*", True),
    ("http://[::1]:8080/*", True),
])
def test_has_concrete_host(pattern, expected):
    assert has_concrete_host(pattern) is expected


@pytest.mark.parametrize("pattern,url", [
    # Das Glob-"*" im Host durfte früher bis in den Pfad eines fremden Hosts reichen.
    ("https://*.example.com/*", "https://evil.com/.example.com/x"),
    ("https://*.example.com/*", "https://evil.com?.example.com/"),
    ("*://api.x.com/*", "https://evil.com/?r=https://api.x.com/y"),
    # Userinfo-Trick: Host ist evil.com
    ("https://api.example.com/*", "https://api.example.com@evil.com/"),
    # Port und Schema gehören zum Muster
    ("http://192.168.1.20:8080/*", "http://192.168.1.2:8080/a"),
    ("http://192.168.1.20:8080/*", "http://192.168.1.20/a"),
    ("https://api.example.com/*", "http://api.example.com/a"),
    # Steuer-/Leerzeichen: urllib entfernt sie, andere Parser nicht → nie passend
    ("https://api.example.com/*", "https://api.exa\nmple.com/x"),
    ("https://api.example.com/*", "https://api.example.com\t.evil.com/"),
    ("https://api.example.com/*", "https://api.example.com/x y"),
    # Backslash & Co. sind in Hostnamen ungültig — urllib lässt sie im Host stehen
    ("https://*.example.com/*", "https://evil.com\\api.example.com/"),
])
def test_matches_url_bindet_an_den_host(pattern, url):
    assert matches_url(pattern, url) is False


@pytest.mark.parametrize("pattern,url", [
    ("https://*.example.com/*", "https://api.example.com/x"),
    ("https://api.example.com/*", "https://API.example.com/v1?q=1"),
    ("*://api.x.com/*", "http://api.x.com/y"),
    ("http://192.168.1.20:8080/*", "http://192.168.1.20:8080/a"),
    ("https://api.example.com/v1/*", "https://api.example.com/v1/items"),
    ("https://eutils.ncbi.nlm.nih.gov/*", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed"),
    ("https://www.ebi.ac.uk/europepmc/*", "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=x"),
    ("http://[::1]:8080/*", "http://[::1]:8080/health"),
    # Altbestand ohne Schema: Verhalten bei ausdrücklicher Wahl unverändert
    ("*github.com*", "https://github.com/foo"),
])
def test_matches_url_erlaubt_den_eigenen_host(pattern, url):
    assert matches_url(pattern, url) is True


def test_matches_url_pfad_bleibt_teil_des_musters():
    assert matches_url("https://api.example.com/v1/*", "https://api.example.com/v2/x") is False


def _save(user: str, name: str, pattern: str, value: str = TOKEN) -> None:
    from hydrahive.credentials import store
    ok, err = store.save_credential(user, Credential(name=name, type="bearer", value=value,
                                                     url_pattern=pattern))
    assert ok, err


def test_wildcard_wird_nie_eingesetzt_auch_nicht_per_name(setup_test_env):
    """Auch ausdrücklich genannt nicht: Profilnamen stehen im auth_used-Feld jedes
    fetch_url-Ergebnisses — eine Prompt-Injection könnte sie sonst einfach nennen."""
    from hydrahive.credentials import store
    _save("cred-u1", "alles", "*")
    try:
        assert store.match_credential("cred-u1", "https://attacker.example/x") is None
        assert store.match_credential("cred-u1", "https://attacker.example/x", prefer_name="alles") is None
    finally:
        store.delete_credential("cred-u1", "alles")


def test_per_name_nur_fuer_den_eigenen_host(setup_test_env):
    from hydrahive.credentials import store
    _save("cred-u7", "gh", "https://api.github.example/*")
    try:
        assert store.match_credential("cred-u7", "https://api.github.example/repos",
                                      prefer_name="gh").name == "gh"
        assert store.match_credential("cred-u7", "https://attacker.example/x", prefer_name="gh") is None
    finally:
        store.delete_credential("cred-u7", "gh")


def test_konkreter_host_wird_nur_fuer_diesen_host_eingesetzt(setup_test_env):
    from hydrahive.credentials import store
    _save("cred-u2", "wetter", "https://api.wetter.example/*")
    try:
        assert store.match_credential("cred-u2", "https://api.wetter.example/v1?q=a").name == "wetter"
        assert store.match_credential("cred-u2", "https://evil.example/api.wetter.example/") is None
    finally:
        store.delete_credential("cred-u2", "wetter")


def test_fetch_url_schickt_wildcard_secret_nicht_an_fremde_url(setup_test_env, monkeypatch):
    from hydrahive.credentials import store
    from hydrahive.tools import fetch_url
    from hydrahive.tools.base import ToolContext

    _save("cred-u3", "alles", "*")
    sent: dict = {}

    class _Resp:
        status_code = 200
        headers = {"content-type": "text/plain"}
        text = "ok"
        content = b"ok"
        encoding = "utf-8"

    class _Client:
        def __init__(self, *a, **kw): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def request(self, method, url, headers=None, params=None, **kw):
            sent["headers"] = dict(headers or {})
            sent["params"] = dict(params or {})
            return _Resp()

    monkeypatch.setattr(fetch_url, "safe_async_client", lambda *a, **kw: _Client())
    monkeypatch.setattr(fetch_url, "_is_blocked", lambda host: False)
    ctx = ToolContext(session_id="s", agent_id="a", user_id="cred-u3", workspace=Path("/tmp"))
    try:
        asyncio.run(fetch_url._execute({"url": "https://attacker.example/x"}, ctx))
        assert "Authorization" not in sent.get("headers", {})
        assert TOKEN not in str(sent)
    finally:
        store.delete_credential("cred-u3", "alles")


def test_fetch_url_unpassendes_profil_per_name_bricht_ab(setup_test_env, monkeypatch):
    from hydrahive.credentials import store
    from hydrahive.tools import fetch_url
    from hydrahive.tools.base import ToolContext

    _save("cred-u8", "alles", "*")
    sent: list = []
    monkeypatch.setattr(fetch_url, "safe_async_client", lambda *a, **kw: sent.append(1))
    monkeypatch.setattr(fetch_url, "_is_blocked", lambda host: False)
    ctx = ToolContext(session_id="s", agent_id="a", user_id="cred-u8", workspace=Path("/tmp"))
    try:
        res = asyncio.run(fetch_url._execute({"url": "https://attacker.example/x", "auth": "alles"}, ctx))
        assert not res.success
        assert "alles" in res.error and TOKEN not in res.error
        assert sent == []  # kein Request rausgegangen
    finally:
        store.delete_credential("cred-u8", "alles")


def test_credential_werte_werden_aus_tool_output_geschwaerzt(setup_test_env):
    from hydrahive.credentials import redaction, store
    _save("cred-u4", "echo", "https://echo.example/*")
    try:
        assert TOKEN in redaction.user_secret_values("cred-u4")
        assert redaction.user_secret_values("niemand") == set()
    finally:
        store.delete_credential("cred-u4", "echo")


def test_basic_auth_auch_base64_und_passwort_allein(setup_test_env):
    import base64

    from hydrahive.credentials import redaction, store
    pw = "geheim-" + "p" * 16
    ok, err = store.save_credential("cred-u5", Credential(
        name="nas", type="basic", value=f"backup:{pw}", url_pattern="https://nas.example/*"))
    assert ok, err
    try:
        vals = redaction.user_secret_values("cred-u5")
        assert f"backup:{pw}" in vals
        assert pw in vals  # Passwort allein (z.B. aus einer Konfigdatei gelesen)
        assert base64.b64encode(f"backup:{pw}".encode()).decode() in vals  # gespiegelter Header
    finally:
        store.delete_credential("cred-u5", "nas")


def test_ssh_key_zeilen_ja_pem_rahmen_nein(setup_test_env):
    from hydrahive.credentials import redaction, store
    body = "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW"
    key = f"-----BEGIN OPENSSH PRIVATE KEY-----\n{body}\n-----END OPENSSH PRIVATE KEY-----\n"
    ok, err = store.save_credential("cred-u6", Credential(
        name="srv", type="ssh_key", value=key, url_pattern="192.168.1.30", header_name="root"))
    assert ok, err
    try:
        vals = redaction.user_secret_values("cred-u6")
        assert body in vals
        # Die Rahmenzeilen sind nicht geheim — sonst würde jede Doku über SSH-Keys geschwärzt.
        assert "-----BEGIN OPENSSH PRIVATE KEY-----" not in vals
        assert "-----END OPENSSH PRIVATE KEY-----" not in vals
    finally:
        store.delete_credential("cred-u6", "srv")


def test_dispatcher_schwaerzt_credential_echo(client):
    from hydrahive.credentials import store
    from hydrahive.db import init_db
    from hydrahive.db import messages as messages_db
    from hydrahive.db import sessions as sessions_db
    from hydrahive.runner.dispatcher import execute_tool
    from hydrahive.tools import REGISTRY
    from hydrahive.tools.base import Tool, ToolContext, ToolResult

    init_db()
    _save("admin", "echo-test", "https://echo.example/*")
    name = "fake_echo_tool"

    async def _execute(args, ctx):
        return ToolResult.ok({"body": f"Authorization: Bearer {TOKEN}"})

    REGISTRY[name] = Tool(name=name, description="", schema={}, execute=_execute, category="web")
    try:
        s = sessions_db.create(agent_id="a", user_id="admin")
        m = messages_db.append(s.id, "assistant", "tool call")
        ctx = ToolContext(session_id=s.id, agent_id="a", user_id="admin", workspace=Path("/tmp"))
        result, _rid, _ms = asyncio.run(
            execute_tool({"name": name, "input": {}, "id": "tu1"}, [name], ctx, m.id))
        assert TOKEN not in result.output["body"]
        assert "[REDACTED]" in result.output["body"]
    finally:
        REGISTRY.pop(name, None)
        store.delete_credential("admin", "echo-test")


def test_api_liefert_host_bound_fuer_die_warnung(client, auth_headers):
    body = {"name": "api-alles", "type": "bearer", "value": TOKEN, "url_pattern": "*"}
    r = client.post("/api/credentials", json=body, headers=auth_headers)
    assert r.status_code == 201, r.text
    assert r.json()["host_bound"] is False
    assert TOKEN not in r.text

    body = {"name": "api-host", "type": "bearer", "value": TOKEN,
            "url_pattern": "https://api.example.com/*"}
    r = client.post("/api/credentials", json=body, headers=auth_headers)
    assert r.status_code == 201, r.text
    assert r.json()["host_bound"] is True

    listing = {c["name"]: c for c in client.get("/api/credentials", headers=auth_headers).json()}
    assert listing["api-alles"]["host_bound"] is False
    assert listing["api-host"]["host_bound"] is True
    for name in ("api-alles", "api-host"):
        client.delete(f"/api/credentials/{name}", headers=auth_headers)


def test_bearbeiten_ohne_neuen_wert_behaelt_den_gespeicherten(client, auth_headers):
    """Der Editor schickt das Wertfeld leer mit, wenn man nur das Muster ändert
    (Wert ist in der Liste maskiert). Das darf den gespeicherten Wert nicht löschen
    — sonst zerstört das Nachtragen des Hosts z.B. das Passwort eines SMB-Mounts."""
    body = {"name": "edit-muster", "type": "basic", "value": f"user:{TOKEN}", "url_pattern": "*"}
    assert client.post("/api/credentials", json=body, headers=auth_headers).status_code == 201
    body = {**body, "value": "", "url_pattern": "https://nas.example/*"}
    r = client.post("/api/credentials", json=body, headers=auth_headers)
    assert r.status_code == 201, r.text
    got = client.get("/api/credentials/edit-muster?reveal=true", headers=auth_headers).json()
    assert got["value"] == f"user:{TOKEN}"
    assert got["url_pattern"] == "https://nas.example/*"
    assert got["host_bound"] is True
    client.delete("/api/credentials/edit-muster", headers=auth_headers)
