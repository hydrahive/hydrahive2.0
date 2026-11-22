"""Vault-Werkzeuge nur bei serverseitig entsperrtem Vault (Ziel vault-agenten §1.1–1.3, Etappe 1a).

Die Sperre sitzt im Dispatcher (execute_tool). Ein Vault-Werkzeug wird bei gesperrtem Vault gar nicht aufgerufen
und liefert den festen Hinweis. Entsperrt wird nur über die Oberfläche (POST /api/vault/unlock); dieselbe Uhr wie
der Vault-Token: 15 min seit der letzten Nutzung, höchstens 8 h, Sperren und PIN-Wechsel schließen sofort.
"""
from __future__ import annotations

import asyncio
import time

import pytest

from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner.dispatcher import execute_tool
from hydrahive.tools import REGISTRY, Tool, ToolContext, ToolResult
from hydrahive.vault import tokens

LOCKED = "Vault gesperrt – bitte in HydraHive entsperren."
PIN = "135790"
PW = "testpass123"
#: Kernliste (Cryptoboard, Patientenakte) und ein Legal-Fall-Werkzeug (Manifest sensitive_tools) – Ziel §1.1
VAULT_TOOLS = ["query_portfolio", "query_fhir_data", "query_health_data", "legal_case"]
PUBLIC_TOOLS = ["query_crypto_price", "query_crypto_analysis"]


@pytest.fixture
def fake_tools(monkeypatch):
    """Werkzeuge mit den echten Namen; zählen, ob sie aufgerufen wurden."""
    calls: list[str] = []

    def _tool(name: str) -> Tool:
        async def _run(args: dict, ctx: ToolContext) -> ToolResult:
            calls.append(name)
            return ToolResult.ok({"daten": f"geheim-{name}"})
        return Tool(name=name, description=name, schema={"type": "object", "properties": {}}, execute=_run)

    for name in VAULT_TOOLS + PUBLIC_TOOLS:
        monkeypatch.setitem(REGISTRY, name, _tool(name))
    return calls


@pytest.fixture
def legal_module(monkeypatch):
    """Legal als geladenes Vault-Modul mit sensitive_tools (wie das echte Manifest)."""
    from hydrahive.modules.manifest import ModuleManifest
    from hydrahive.modules.registry import REGISTRY as MODS, LoadedModule
    mf = ModuleManifest(id="legal", name="Recht", version="1.0.0", vault=True,
                        sensitive_tools=(("legal_case", "privat"),))
    monkeypatch.setitem(MODS, "legal", LoadedModule(name="legal", manifest=mf, path=None, loaded=True))


def _close(user_id: str) -> None:
    try:
        from hydrahive.vault import unlocks
    except ImportError:          # Gegenprobe ohne Fix: Modul fehlt noch
        return
    unlocks.close(user_id)


@pytest.fixture
def uid(client, auth_headers):
    from hydrahive.api.middleware import users
    from hydrahive.vault import lockout, pins
    u = users.verify("testuser", PW)["user_id"]
    pins.reset(u)
    _close(u)
    lockout.clear()
    client.post("/api/vault/setup", json={"password": PW, "pin": PIN}, headers=auth_headers)
    _close(u)   # PIN festlegen entsperrt die Oberfläche; die Tests starten gesperrt
    yield u
    pins.reset(u)
    _close(u)
    lockout.clear()


def _call(name: str, tmp_path, *, user: str = "testuser", args: dict | None = None):
    s = sessions_db.create(agent_id="a1", user_id=user, title="vault-gate")
    msg = messages_db.append(s.id, "assistant", "hi")
    ctx = ToolContext(session_id=s.id, agent_id="a1", user_id=user, workspace=tmp_path)
    tool_use = {"id": f"tu-{name}", "name": name, "input": args or {}}
    result, _, _ = asyncio.run(execute_tool(tool_use, [name], ctx, msg.id))
    return result


def _unlock(client, auth_headers) -> str:
    r = client.post("/api/vault/unlock", json={"pin": PIN}, headers=auth_headers)
    assert r.status_code == 200, r.text
    return r.json()["vault_token"]


def _shift(monkeypatch, seconds: float) -> None:
    """Uhr vorstellen – gilt für Token (vault/gate.py) und Entsperr-Zustand gleichermaßen."""
    monkeypatch.setattr(time, "time", lambda real=time.time: real() + seconds)


# ── V1: gesperrt → keine Daten, Werkzeug wird nicht aufgerufen ─────────────────────────────────────────────────

@pytest.mark.parametrize("name", VAULT_TOOLS)
def test_gesperrt_liefert_hinweis_statt_daten(name, uid, fake_tools, legal_module, tmp_path):
    result = _call(name, tmp_path)
    assert result.success is False and result.error == LOCKED
    assert "geheim" not in result.to_llm()
    assert fake_tools == [], "Werkzeug darf bei gesperrtem Vault gar nicht laufen"


def test_ohne_pin_gesperrt(client, auth_headers, fake_tools, tmp_path):
    from hydrahive.api.middleware import users
    from hydrahive.vault import pins
    u = users.verify("testuser", PW)["user_id"]
    pins.reset(u)
    _close(u)
    assert _call("query_portfolio", tmp_path).error == LOCKED and fake_tools == []


def test_unbekannter_nutzer_gesperrt(uid, fake_tools, tmp_path):
    """user_id_for(username) → None: fail closed."""
    assert _call("query_portfolio", tmp_path, user="gibt-es-nicht").error == LOCKED and fake_tools == []


# ── V2: entsperrt → Daten; Ablauf, Sperren, PIN-Wechsel → wieder gesperrt ─────────────────────────────────────

@pytest.mark.parametrize("name", VAULT_TOOLS)
def test_entsperrt_liefert_daten(name, client, auth_headers, uid, fake_tools, legal_module, tmp_path):
    _unlock(client, auth_headers)
    result = _call(name, tmp_path)
    assert result.success is True and result.output == {"daten": f"geheim-{name}"}
    assert fake_tools == [name]


def test_nach_15_min_ohne_nutzung_gesperrt(client, auth_headers, uid, fake_tools, tmp_path, monkeypatch):
    _unlock(client, auth_headers)
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + tokens.IDLE_SECONDS - 30)
    assert _call("query_portfolio", tmp_path).success is True        # kurz vor Ablauf: noch offen, verlängert
    monkeypatch.setattr(time, "time", lambda: real() + 2 * tokens.IDLE_SECONDS)   # danach 15 min + 30 s Ruhe
    assert _call("query_portfolio", tmp_path).error == LOCKED


def test_nutzung_verlaengert_hoechstens_8_stunden(client, auth_headers, uid, fake_tools, tmp_path, monkeypatch):
    _unlock(client, auth_headers)
    real = time.time
    step = tokens.IDLE_SECONDS - 60
    t = 0
    while t + step < tokens.MAX_SECONDS:
        t += step
        monkeypatch.setattr(time, "time", lambda t=t: real() + t)
        assert _call("query_portfolio", tmp_path).success is True, f"nach {t} s noch offen erwartet"
    monkeypatch.setattr(time, "time", lambda: real() + tokens.MAX_SECONDS + 1)
    assert _call("query_portfolio", tmp_path).error == LOCKED


def test_oberflaeche_verlaengert_auch(client, auth_headers, uid, fake_tools, tmp_path, monkeypatch):
    """Eine Vault-Anfrage der Oberfläche (require_vault_unlocked) schiebt die Uhr auch für Agenten weiter."""
    tok = _unlock(client, auth_headers)
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + tokens.IDLE_SECONDS - 60)
    r = client.get("/api/credentials", headers={**auth_headers, "X-HH-Vault": tok})
    assert r.status_code == 200, r.text
    monkeypatch.setattr(time, "time", lambda: real() + 2 * tokens.IDLE_SECONDS - 120)
    assert _call("query_portfolio", tmp_path).success is True


def test_sperren_schliesst_sofort(client, auth_headers, uid, fake_tools, tmp_path):
    _unlock(client, auth_headers)
    assert _call("query_portfolio", tmp_path).success is True
    assert client.post("/api/vault/lock", headers=auth_headers).status_code == 200
    assert _call("query_portfolio", tmp_path).error == LOCKED


def test_pin_wechsel_schliesst_sofort(client, auth_headers, uid, fake_tools, tmp_path):
    _unlock(client, auth_headers)
    r = client.post("/api/vault/reset", json={"password": PW, "pin": "246802"}, headers=auth_headers)
    assert r.status_code == 200
    _close_check = _call("query_portfolio", tmp_path)
    assert _close_check.error == LOCKED, "neue PIN gibt der Oberfläche einen Token, Agenten bleiben gesperrt"


def test_pin_wechsel_anderswo_schliesst_sofort(client, auth_headers, uid, fake_tools, tmp_path):
    """Auch wenn die generation an anderer Stelle hochgeht (pins.set_pin/bump), gilt der alte Zustand nicht."""
    _unlock(client, auth_headers)
    from hydrahive.vault import pins
    pins.bump(uid)
    assert _call("query_portfolio", tmp_path).error == LOCKED


def test_admin_reset_schliesst_sofort(client, auth_headers, admin_headers, uid, fake_tools, tmp_path):
    _unlock(client, auth_headers)
    assert client.post(f"/api/vault/admin/reset/{uid}", headers=admin_headers).status_code == 200
    assert _call("query_portfolio", tmp_path).error == LOCKED


def test_zustand_liegt_in_der_datenbank(client, auth_headers, uid):
    """Neustart/mehrere Worker: der Zustand kommt aus der DB, nicht aus dem Prozessspeicher."""
    _unlock(client, auth_headers)
    from hydrahive.db.connection import db
    with db() as c:
        row = c.execute("SELECT unlocked_at, last_used_at, generation FROM vault_unlocks WHERE user_id = ?",
                        (uid,)).fetchone()
    assert row is not None and row["unlocked_at"] > 0 and row["last_used_at"] >= row["unlocked_at"]


# ── Auftrag 2d / V5: andere Werkzeuge laufen immer ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", PUBLIC_TOOLS)
def test_oeffentliche_werkzeuge_frei(name, uid, fake_tools, tmp_path):
    result = _call(name, tmp_path)
    assert result.success is True and fake_tools == [name]


def test_kernwerkzeug_frei(uid, tmp_path):
    (tmp_path / "notiz.txt").write_text("hallo")
    result = _call("file_read", tmp_path, args={"path": "notiz.txt"})
    assert result.success is True and "hallo" in result.to_llm()


def test_mail_bleibt_frei():
    """Ziel §1.7: Mail-Werkzeuge sind sensibel (Datamining), aber keine Vault-Werkzeuge."""
    from hydrahive.vault.agent_gate import vault_tools
    names = vault_tools()
    assert {"query_portfolio", "query_fhir_data", "query_health_data"} <= names
    assert "read_mail" not in names and "send_mail" not in names


def test_sensitive_tools_eines_nicht_vault_moduls_frei(monkeypatch):
    from hydrahive.modules.manifest import ModuleManifest
    from hydrahive.modules.registry import REGISTRY as MODS, LoadedModule
    mf = ModuleManifest(id="notiz", name="Notiz", version="1.0.0", sensitive_tools=(("notiz_lesen", "privat"),))
    monkeypatch.setitem(MODS, "notiz", LoadedModule(name="notiz", manifest=mf, path=None, loaded=True))
    from hydrahive.vault.agent_gate import vault_tools
    assert "notiz_lesen" not in vault_tools()
