"""send_mail-Tool: Tool-Config-Override → Fallback auf globale Mail-Settings.

Single Source: ohne Agent-eigene `smtp`-Tool-Config zieht das Tool die globalen
Mail-Settings (dieselbe Quelle wie der Watcher) — keine Doppel-Config, kein
zweites Passwort an zweiter Stelle. Die Tool-Config bleibt als optionaler
Per-Agent-Override (Naht für „Postfach pro Buddy").

Lazy imports wegen der settings.data_dir-Freeze-Falle.
"""
from __future__ import annotations

import asyncio
from pathlib import Path


def _ctx(config):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="s", agent_id="a", user_id="u",
                       workspace=Path("/tmp"), config=config)


# ---------------------------------------------------------------- Config-Auflösung

def test_resolve_prefers_tool_config_override(monkeypatch):
    from hydrahive.tools import send_mail
    monkeypatch.setattr(send_mail, "_settings_smtp",
                        lambda: {"host": "global.host", "from": "global@x"})
    cfg = send_mail._resolve_smtp_cfg(
        {"smtp": {"host": "agent.host", "from": "agent@x", "user": "u", "password": "p"}})
    assert cfg["host"] == "agent.host"
    assert cfg["from"] == "agent@x"


def test_resolve_falls_back_to_settings_when_no_override(monkeypatch):
    from hydrahive.tools import send_mail
    monkeypatch.setattr(send_mail, "_settings_smtp",
                        lambda: {"host": "global.host", "from": "global@x"})
    cfg = send_mail._resolve_smtp_cfg({})
    assert cfg["host"] == "global.host"
    assert cfg["from"] == "global@x"


def test_resolve_ignores_incomplete_override(monkeypatch):
    # Tool-Config ohne host/from ist kein gültiger Override → Settings gewinnen
    from hydrahive.tools import send_mail
    monkeypatch.setattr(send_mail, "_settings_smtp",
                        lambda: {"host": "global.host", "from": "global@x"})
    cfg = send_mail._resolve_smtp_cfg({"smtp": {"user": "only-user"}})
    assert cfg["host"] == "global.host"


# ---------------------------------------------------------------- _execute

def test_execute_sends_via_settings_fallback(monkeypatch):
    from hydrahive.tools import send_mail
    monkeypatch.setattr(send_mail, "_settings_smtp",
                        lambda: {"host": "global.host", "port": 587, "user": "u",
                                 "password": "p", "from": "bot@x", "use_tls": True})
    sent = {}

    def fake_send(cfg, msg):
        sent["host"] = cfg["host"]
        sent["from"] = msg["From"]
        sent["to"] = msg["To"]

    from hydrahive.communication.mail import _transport
    monkeypatch.setattr(_transport, "send_message", fake_send)

    res = asyncio.run(send_mail._execute(
        {"to": "x@y", "subject": "Hi", "body": "yo"}, _ctx({})))
    assert res.success
    assert sent["host"] == "global.host"
    assert sent["from"] == "bot@x"
    assert sent["to"] == "x@y"


def test_execute_stub_when_nothing_configured(monkeypatch):
    from hydrahive.tools import send_mail
    monkeypatch.setattr(send_mail, "_settings_smtp", lambda: {"host": "", "from": ""})
    res = asyncio.run(send_mail._execute(
        {"to": "x@y", "subject": "Hi", "body": "yo"}, _ctx({})))
    assert not res.success
    assert "Stub" in res.error


# ---------------------------------------------------------------- From-Validierung

def test_execute_rejects_from_without_address(monkeypatch):
    # KAS gibt sonst nur kryptisch "504 need fully-qualified address" zurück.
    from hydrahive.tools import send_mail
    from hydrahive.communication.mail import _transport
    monkeypatch.setattr(send_mail, "_settings_smtp",
                        lambda: {"host": "w0.kasserver.com", "from": "Agenttest"})
    called = {"sent": False}
    monkeypatch.setattr(_transport, "send_message",
                        lambda cfg, msg: called.update(sent=True))

    res = asyncio.run(send_mail._execute(
        {"to": "x@y.de", "subject": "Hi", "body": "yo"}, _ctx({})))
    assert not res.success
    assert "Agenttest" in res.error          # nennt den fehlerhaften Wert
    assert called["sent"] is False           # gar nicht erst verbunden


def test_execute_accepts_display_name_address(monkeypatch):
    from hydrahive.tools import send_mail
    from hydrahive.communication.mail import _transport
    monkeypatch.setattr(send_mail, "_settings_smtp",
                        lambda: {"host": "w0.kasserver.com", "port": 465,
                                 "from": "Agent Test <agenttest@hydrahive.org>"})
    sent = {}
    monkeypatch.setattr(_transport, "send_message",
                        lambda cfg, msg: sent.update(frm=msg["From"]))

    res = asyncio.run(send_mail._execute(
        {"to": "x@y.de", "subject": "Hi", "body": "yo"}, _ctx({})))
    assert res.success
    assert sent["frm"] == "Agent Test <agenttest@hydrahive.org>"
