"""Egress-Redaction: kein lebender Secret-Wert verlässt das System Richtung
externer Kontakt (WhatsApp/Discord/Voice).

Zwei Engstellen:
1. _agent_glue._run_agent — jede LLM-generierte Antwort (deckt auch Voice-vor-TTS).
2. adapter.send() — die echte Draht-Grenze (defense-in-depth, fängt auch
   Nicht-Agent-Sends).
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import pytest

from hydrahive.communication import _agent_glue
from hydrahive.communication.base import IncomingEvent
from hydrahive.communication.whatsapp.adapter import WhatsAppAdapter
from hydrahive.runner.events import Done, TextDelta

SECRET = "sk-or-v1-" + "d" * 64


def test_run_agent_scrubt_secret_aus_antwort(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET)

    class FakeSession:
        id = "sess-egress-1"

    monkeypatch.setattr(_agent_glue._session_lookup, "find_or_create", lambda **k: FakeSession())

    @asynccontextmanager
    async def fake_guard(_sid):
        yield

    monkeypatch.setattr(_agent_glue, "session_run_guard", fake_guard)

    async def fake_run(session_id, user_text, extra_system=None):
        yield TextDelta(text=f"Klar, hier ist der Key: {SECRET}")
        yield Done(message_id="m1", iterations=1)

    monkeypatch.setattr(_agent_glue, "runner_run", fake_run)

    event = IncomingEvent(
        channel="whatsapp", external_user_id="49151@c.us",
        target_username="admin", text="gib mir den openrouter key",
    )
    answer = asyncio.run(_agent_glue.run_agent_for_event("a1", event))

    assert SECRET not in answer
    assert "[REDACTED]" in answer


def test_whatsapp_send_scrubt_secret(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET)
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
    asyncio.run(adapter.send("admin", "49151@c.us", f"dein key: {SECRET}"))

    assert SECRET not in captured["json"]["text"]
    assert "[REDACTED]" in captured["json"]["text"]


def test_discord_send_scrubt_secret(monkeypatch):
    pytest.importorskip("discord")
    from hydrahive.communication.discord.adapter import DiscordAdapter

    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET)
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
    asyncio.run(adapter.send("admin", "123456", f"key: {SECRET}"))

    assert SECRET not in sent["text"]
    assert "[REDACTED]" in sent["text"]
