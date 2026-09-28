"""Egress-Schwärzung kennt auch die Credential-Werte des Nutzers.

Vorher schwärzten Discord-/WhatsApp-Ausgang und die Discord-Werkzeuge nur
System-Secrets (env, LLM-Config), Agent-Secrets und den Bot-Token. Ein per
fetch_url gespiegelter Vault-Token des Nutzers wäre so nach außen gegangen.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import pytest

from hydrahive.communication import _agent_glue
from hydrahive.communication.base import IncomingEvent
from hydrahive.runner.events import Done, TextDelta

USER_TOKEN = "vault-" + "u" * 40


@pytest.fixture(autouse=True)
def _user_secret(monkeypatch):
    monkeypatch.setattr(
        "hydrahive.credentials.secret_sources.user_secret_values",
        lambda username: {USER_TOKEN} if username == "admin" else set(),
    )
    monkeypatch.setattr(
        "hydrahive.credentials.redaction.user_secret_values",
        lambda username: {USER_TOKEN} if username == "admin" else set(),
    )


def test_agent_antwort_schwaerzt_nutzer_credential(monkeypatch):
    class FakeSession:
        id = "sess-egress-u1"

    monkeypatch.setattr(_agent_glue._session_lookup, "find_or_create", lambda **k: FakeSession())

    @asynccontextmanager
    async def fake_guard(_sid):
        yield

    monkeypatch.setattr(_agent_glue, "session_run_guard", fake_guard)

    async def fake_run(session_id, user_text, extra_system=None):
        yield TextDelta(text=f"Dein Token lautet {USER_TOKEN}")
        yield Done(message_id="m1", iterations=1)

    monkeypatch.setattr(_agent_glue, "runner_run", fake_run)
    event = IncomingEvent(channel="discord", external_user_id="5:1", target_username="admin", text="token?")
    answer = asyncio.run(_agent_glue.run_agent_for_event("a1", event))
    assert USER_TOKEN not in answer and "[REDACTED]" in answer


def test_whatsapp_send_schwaerzt_nutzer_credential(monkeypatch):
    from hydrahive.communication.whatsapp.adapter import WhatsAppAdapter
    adapter = WhatsAppAdapter("http://bridge.local")
    captured: dict = {}

    class FakeResp:
        def raise_for_status(self):
            pass

    class FakeClient:
        async def post(self, url, json=None):
            captured["json"] = json
            return FakeResp()

    async def fake_http():
        return FakeClient()

    monkeypatch.setattr(adapter, "_http", fake_http)
    asyncio.run(adapter.send("admin", "49151@c.us", f"key: {USER_TOKEN}"))
    assert USER_TOKEN not in captured["json"]["text"]


def test_discord_send_schwaerzt_nutzer_credential(monkeypatch):
    pytest.importorskip("discord")
    from hydrahive.communication.discord.adapter import DiscordAdapter
    adapter = DiscordAdapter()
    sent: dict = {}

    class FakeChannel:
        async def send(self, text):
            sent["text"] = text

    class FakeClient:
        def is_ready(self):
            return True

        async def fetch_channel(self, _cid):
            return FakeChannel()

    adapter._clients["admin"] = FakeClient()
    asyncio.run(adapter.send("admin", "123456", f"key: {USER_TOKEN}"))
    assert USER_TOKEN not in sent["text"]


def test_discord_werkzeug_egress_schwaerzt_nutzer_credential():
    pytest.importorskip("discord")
    from hydrahive.communication.discord import config as dc
    from hydrahive.communication.discord.ops_access import Scope, egress_scrub
    scope = Scope(username="admin", client=object(), cfg=dc.DiscordConfig())
    assert USER_TOKEN not in egress_scrub(scope, "agent-x", f"hier: {USER_TOKEN}")


def test_send_mail_werkzeug_schwaerzt_nutzer_credential(monkeypatch):
    from hydrahive.communication.mail import _transport
    from hydrahive.tools import send_mail
    from hydrahive.tools.base import ToolContext
    from pathlib import Path

    monkeypatch.setattr(send_mail, "_settings_smtp",
                        lambda: {"host": "smtp.example", "port": 587, "user": "u", "password": "p",
                                 "from": "buddy@example.org", "use_tls": True})
    sent: dict = {}

    def fake_send(cfg, msg):
        sent["body"] = msg.get_content()
        sent["subject"] = msg["Subject"]

    monkeypatch.setattr(_transport, "send_message", fake_send)
    ctx = ToolContext(session_id="s", agent_id="a", user_id="admin", workspace=Path("/tmp"), config={})
    res = asyncio.run(send_mail.TOOL.execute(
        {"to": "x@example.org", "subject": f"Token {USER_TOKEN}", "body": f"Hier: {USER_TOKEN}"}, ctx))
    assert res.success, res.error
    assert USER_TOKEN not in sent["body"] and USER_TOKEN not in sent["subject"]
