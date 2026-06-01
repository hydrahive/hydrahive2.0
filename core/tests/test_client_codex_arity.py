"""client.complete entpackt das codex_call-Tupel korrekt (Issue #200, adjacent).

codex_call liefert (blocks, stop_reason, usage); client.complete entpackte nur
2 Werte → ValueError auf dem openai-codex/-Pfad. Jetzt 3-stellig.
"""
from __future__ import annotations

import asyncio


def test_complete_codex_path_unpacks_three_tuple(monkeypatch):
    from hydrahive.llm import client

    monkeypatch.setattr(client, "load_config", lambda: {"default_model": "openai-codex/gpt-5"})

    async def _fake_token():
        return {"access": "tok", "account_id": "acc"}

    async def _fake_codex_call(**kwargs):
        return ([{"type": "text", "text": "hallo"}], "end_turn", {"input_tokens": 1})

    monkeypatch.setattr("hydrahive.oauth.openai_codex.resolve_openai_codex_token", _fake_token)
    monkeypatch.setattr("hydrahive.runner._codex_provider.codex_call", _fake_codex_call)

    result = asyncio.run(client.complete([{"role": "user", "content": "hi"}]))
    assert result == "hallo"
