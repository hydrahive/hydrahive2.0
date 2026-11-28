"""Codex lehnt ein Modell fürs ChatGPT-Konto ab → Meldung nennt keine festen Modelle (Task c07187d6).

Vorher empfahl der Text „gpt-5.2, gpt-5.4 oder gpt-5.5“ – bei Tills Konto gingen genau die nicht.
"""
from __future__ import annotations

import asyncio
import re

import httpx
import pytest

from hydrahive.runner import _codex_provider as mod

BODY = '{"detail": "The model is not supported when using Codex with a ChatGPT account."}'


def test_meldung_ohne_feste_modelle(monkeypatch):
    original = httpx.AsyncClient
    transport = httpx.MockTransport(lambda req: httpx.Response(400, text=BODY))
    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda **kw: original(transport=transport, **kw))

    async def go():
        async for _ in mod.codex_stream(access_token="t", account_id="a", model="gpt-x",
                                        system_prompt="", messages=[], tools=[]):
            pass

    with pytest.raises(mod.CodexModelNotAllowed) as e:
        asyncio.run(go())
    text = str(e.value)
    assert "gpt-x" in text
    assert not re.search(r"gpt-\d", text.replace("gpt-x", ""))
    assert "KI-Modelle" in text
