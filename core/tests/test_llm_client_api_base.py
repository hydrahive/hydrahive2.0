"""llm.client complete()/stream() nutzen die api_base des Anbieters (docs/specs/llm-client-api-base.md)."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from hydrahive.llm import client

CFG = {
    "default_model": "openai/x",
    "providers": [
        {"id": "openai", "api_key": "k", "api_base": "http://lan-box:8000/v1/"},
        {"id": "ollama", "api_base": "http://gpu-box:11434"},
        {"id": "groq", "api_key": "g"},
    ],
}


@pytest.fixture
def calls(monkeypatch):
    seen: list[dict] = []

    async def fake_acompletion(**kwargs):
        seen.append(kwargs)
        if kwargs.get("stream"):
            async def gen():
                yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="a"))])
                yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="b"))])
            return gen()
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])

    monkeypatch.setattr(client, "load_config", lambda: CFG)
    monkeypatch.setattr(client, "apply_keys", lambda cfg: None)
    monkeypatch.setattr(client.litellm, "acompletion", fake_acompletion)
    return seen


def _stream(model: str) -> str:
    async def run():
        return "".join([c async for c in client.stream([{"role": "user", "content": "hi"}], model=model)])
    return asyncio.run(run())


def test_complete_uses_api_base_of_provider(calls):
    assert asyncio.run(client.complete([{"role": "user", "content": "hi"}], model="openai/x")) == "ok"
    assert calls[-1]["api_base"] == "http://lan-box:8000/v1"           # ohne Schrägstrich am Ende


def test_stream_uses_api_base_of_provider(calls):
    assert _stream("openai/x") == "ab"
    assert calls[-1]["api_base"] == "http://lan-box:8000/v1" and calls[-1]["stream"] is True


def test_no_api_base_argument_without_configured_address(calls):
    asyncio.run(client.complete([{"role": "user", "content": "hi"}], model="groq/llama"))
    _stream("groq/llama")
    assert all("api_base" not in c for c in calls)                       # Cloud-Ziel bleibt
    assert all("num_ctx" not in c and "extra_body" not in c for c in calls)


def test_ollama_gets_api_base_and_num_ctx(calls):
    asyncio.run(client.complete([{"role": "user", "content": "hi"}], model="ollama/llama3"))
    _stream("ollama/llama3")
    for c in calls:
        assert c["api_base"] == "http://gpu-box:11434"
        assert isinstance(c["num_ctx"], int) and c["num_ctx"] > 4096
        assert c["extra_body"] == {"options": {"num_ctx": c["num_ctx"]}}


def test_default_model_also_uses_api_base(calls):
    asyncio.run(client.complete([{"role": "user", "content": "hi"}]))   # default_model = openai/x
    assert calls[-1]["model"] == "openai/x" and calls[-1]["api_base"] == "http://lan-box:8000/v1"


def test_api_base_for_lives_in_llm_config_and_runner_uses_it():
    from hydrahive.llm._config import api_base_for
    from hydrahive.runner import llm_bridge
    assert llm_bridge._resolve_api_base is api_base_for
    assert api_base_for(CFG, "openai/x") == "http://lan-box:8000/v1"
    assert api_base_for(CFG, "ollama/q") == "http://gpu-box:11434"
    assert api_base_for(CFG, "groq/x") is None
    assert api_base_for(CFG, "claude-sonnet-4-6") is None
    assert api_base_for({"providers": []}, "openai/x") is None
