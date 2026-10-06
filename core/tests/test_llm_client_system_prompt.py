"""llm.client complete()/stream(): role=system-Nachrichten müssen beim Modell ankommen.

Bug (06.10.2026, live auf hydratest belegt): Bei Anthropic-OAuth ersetzte die Identity
(„You are Claude Code…“) die Systemanweisung statt sie zu ergänzen; im Stream wurde sie
gar nicht herausgezogen; der Codex-Weg übergab system_prompt="" und messages_to_codex
verwarf role=system. Betroffen: alle Module/Kernteile, die complete() mit einer
system-Nachricht aufrufen (Deep Research, Zahnfee, Storyteller, Atelier, …).
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.llm import _anthropic_calls as calls_mod
from hydrahive.llm import client as llm_client
from hydrahive.llm._anthropic_calls import split_system

SYS = "Antworte nur mit BANANE."
MSGS = [{"role": "system", "content": SYS}, {"role": "user", "content": "Hauptstadt von Frankreich?"}]


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- split_system
def test_split_system_collects_all_system_texts_in_order():
    sys_text, rest = split_system([
        {"role": "system", "content": "A"}, {"role": "user", "content": "u"},
        {"role": "system", "content": [{"type": "text", "text": "B"}]}, {"role": "assistant", "content": "x"},
    ])
    assert sys_text == "A\n\nB"
    assert [m["role"] for m in rest] == ["user", "assistant"]


def test_split_system_without_system_is_empty():
    assert split_system([{"role": "user", "content": "u"}]) == ("", [{"role": "user", "content": "u"}])


# ---------------------------------------------------------------- Anthropic (SDK gefälscht)
class _Block:
    type = "text"
    text = "OK"


class _Raw:
    headers: dict = {}

    def parse(self):
        from types import SimpleNamespace
        return SimpleNamespace(content=[_Block()])


class _Stream:
    def __init__(self):
        async def gen():
            yield "OK"
        self.text_stream = gen()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def _fake_client(seen: list[dict]):
    class Raw:
        async def create(self, **kw):
            seen.append(kw)
            return _Raw()

    class Messages:
        with_raw_response = Raw()

        async def create(self, **kw):
            seen.append(kw)
            from types import SimpleNamespace
            return SimpleNamespace(content=[_Block()])

        def stream(self, **kw):
            seen.append(kw)
            return _Stream()

    class C:
        messages = Messages()
    return C()


def _system_texts(kw: dict) -> list[str]:
    s = kw.get("system")
    if s is None:
        return []
    if isinstance(s, str):
        return [s]
    return [b["text"] for b in s]


@pytest.mark.parametrize("oauth", [True, False])
def test_anthropic_complete_sends_system(monkeypatch, oauth):
    seen: list[dict] = []
    monkeypatch.setattr(calls_mod, "_client", lambda key: (_fake_client(seen), oauth))
    monkeypatch.setattr("hydrahive.llm._oauth_usage.extract_rate_limit_headers", lambda h: None)
    assert _run(calls_mod.anthropic_complete("k", MSGS, "claude-haiku-4-5", 0.7, 50)) == "OK"
    kw = seen[0]
    texts = _system_texts(kw)
    assert SYS in texts
    assert all(m["role"] != "system" for m in kw["messages"])
    if oauth:  # Identity zuerst, Anweisung zusätzlich
        assert texts[0].startswith("You are Claude Code") and texts[-1] == SYS


@pytest.mark.parametrize("oauth", [True, False])
def test_anthropic_stream_sends_system(monkeypatch, oauth):
    seen: list[dict] = []
    monkeypatch.setattr(calls_mod, "_client", lambda key: (_fake_client(seen), oauth))

    async def collect():
        return "".join([t async for t in calls_mod.anthropic_stream("k", MSGS, "claude-haiku-4-5", 0.7, 50)])
    assert _run(collect()) == "OK"
    kw = seen[0]
    assert SYS in _system_texts(kw)
    assert all(m["role"] != "system" for m in kw["messages"])


def test_anthropic_oauth_without_system_keeps_only_identity(monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(calls_mod, "_client", lambda key: (_fake_client(seen), True))
    monkeypatch.setattr("hydrahive.llm._oauth_usage.extract_rate_limit_headers", lambda h: None)
    _run(calls_mod.anthropic_complete("k", MSGS[1:], "claude-haiku-4-5", 0.7, 50))
    assert len(_system_texts(seen[0])) == 1


@pytest.mark.parametrize("fn", ["minimax_complete", "minimax_stream"])
def test_minimax_sends_system_as_parameter(monkeypatch, fn):
    seen: list[dict] = []

    class FakeAnthropic:
        def __init__(self, **kw):
            self.messages = _fake_client(seen).messages
    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", FakeAnthropic)

    async def go():
        if fn == "minimax_complete":
            return await calls_mod.minimax_complete("k", MSGS, "MiniMax-M2", 0.7, 50)
        return "".join([t async for t in calls_mod.minimax_stream("k", MSGS, "MiniMax-M2", 0.7, 50)])
    assert _run(go()) == "OK"
    assert _system_texts(seen[0]) == [SYS]
    assert all(m["role"] != "system" for m in seen[0]["messages"])


# ---------------------------------------------------------------- Codex-Weg in client.py
def test_codex_complete_passes_system_as_system_prompt(monkeypatch):
    seen: dict = {}

    async def fake_token():
        return {"access": "t", "account_id": "a"}

    async def fake_call(**kw):
        seen.update(kw)
        return [{"type": "text", "text": "OK"}], "stop", {}
    monkeypatch.setattr("hydrahive.oauth.openai_codex.resolve_openai_codex_token", fake_token)
    monkeypatch.setattr("hydrahive.runner._codex_provider.codex_call", fake_call)
    monkeypatch.setattr(llm_client, "load_config", lambda: {"default_model": ""})
    assert _run(llm_client.complete(MSGS, model="openai-codex/gpt-5.6-luna")) == "OK"
    assert seen["system_prompt"] == SYS
    assert all(m["role"] != "system" for m in seen["messages"])


def test_codex_stream_passes_system_as_system_prompt(monkeypatch):
    seen: dict = {}

    async def fake_token():
        return {"access": "t", "account_id": "a"}

    async def fake_stream(**kw):
        seen.update(kw)
        yield {"type": "text_delta", "text": "OK"}
    monkeypatch.setattr("hydrahive.oauth.openai_codex.resolve_openai_codex_token", fake_token)
    monkeypatch.setattr("hydrahive.runner._codex_provider.codex_stream", fake_stream)
    monkeypatch.setattr(llm_client, "load_config", lambda: {"default_model": ""})

    async def collect():
        return "".join([t async for t in llm_client.stream(MSGS, model="openai-codex/gpt-5.6-luna")])
    assert _run(collect()) == "OK"
    assert seen["system_prompt"] == SYS
    assert all(m["role"] != "system" for m in seen["messages"])
