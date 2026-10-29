"""Ollama über /api/chat (Spec docs/specs/ollama-chat-route.md).

LiteLLMs Präfix `ollama/` geht auf /api/generate und rät Werkzeugaufrufe aus Text – lokale Agenten erfanden dadurch
Werkzeuge („none“) oder antworteten leer. `ollama_chat/` nutzt /api/chat mit echtem Werkzeug-Feld. Die Modell-ID in
Konfiguration, Agenten und Protokoll bleibt `ollama/<name>`; nur das Ziel des LiteLLM-Aufrufs wird umgeschrieben.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from hydrahive.llm import client
from hydrahive.llm._routing import litellm_model
from hydrahive.runner import _llm_bridge_backends as backends

CFG = {"default_model": "ollama/gemma4:12b", "providers": [{"id": "ollama", "api_base": "http://gpu-box:11434"},
                                                         {"id": "groq", "api_key": "g"}]}


@pytest.mark.parametrize(("model", "target"), [
    ("ollama/gemma4:12b", "ollama_chat/gemma4:12b"),
    ("ollama/gpt-oss:20b", "ollama_chat/gpt-oss:20b"),
    ("ollama/library/qwen3:8b", "ollama_chat/library/qwen3:8b"),
    ("ollama_chat/gemma4:12b", "ollama_chat/gemma4:12b"),
    ("groq/llama", "groq/llama"),
    ("openai/gpt-x", "openai/gpt-x"),
    ("openrouter/ollama/x", "openrouter/ollama/x"),
    ("claude-sonnet-5", "claude-sonnet-5"),
    ("", ""),
])
def test_litellm_model_schreibt_nur_ollama_auf_api_chat_um(model, target):
    assert litellm_model(model) == target


def _resp():
    msg = SimpleNamespace(content="ok", tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")], usage=None)


@pytest.fixture
def seen(monkeypatch):
    calls: list[dict] = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if kwargs.get("stream"):
            async def gen():
                yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="a"))])
            return gen()
        return _resp()

    import litellm
    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(client.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(client, "load_config", lambda: CFG)
    monkeypatch.setattr(client, "apply_keys", lambda cfg: None)
    return calls


def test_agenten_aufruf_geht_an_api_chat_mit_num_ctx_und_adresse(seen):
    tools = [{"name": "file_read", "description": "d", "input_schema": {"type": "object", "properties": {}}}]
    asyncio.run(backends.litellm_call(model="ollama/gemma4:12b", system_prompt="s",
                                      messages=[{"role": "user", "content": "hi"}], tools=tools, temperature=0.0,
                                      max_tokens=100, api_base="http://gpu-box:11434", num_ctx=16384))
    c = seen[-1]
    assert c["model"] == "ollama_chat/gemma4:12b"
    assert c["api_base"] == "http://gpu-box:11434"
    assert c["num_ctx"] == 16384 and c["extra_body"] == {"options": {"num_ctx": 16384}}
    assert c["tools"] and c["tool_choice"] == "auto"


def test_agenten_aufruf_anderer_anbieter_bleibt_gleich(seen):
    asyncio.run(backends.litellm_call(model="groq/llama", system_prompt="s", messages=[{"role": "user", "content": "x"}],
                                      tools=[], temperature=0.0, max_tokens=100))
    assert seen[-1]["model"] == "groq/llama"
    assert "num_ctx" not in seen[-1] and "extra_body" not in seen[-1]


def test_complete_und_stream_gehen_an_api_chat(seen):
    asyncio.run(client.complete([{"role": "user", "content": "hi"}], model="ollama/gemma4:12b"))

    async def run():
        return [c async for c in client.stream([{"role": "user", "content": "hi"}], model="ollama/gemma4:12b")]
    asyncio.run(run())
    assert [c["model"] for c in seen] == ["ollama_chat/gemma4:12b", "ollama_chat/gemma4:12b"]
    assert all(c["api_base"] == "http://gpu-box:11434" and c["num_ctx"] > 4096 for c in seen)


def test_complete_cloud_bleibt_gleich(seen):
    asyncio.run(client.complete([{"role": "user", "content": "hi"}], model="groq/llama"))
    assert seen[-1]["model"] == "groq/llama"


def test_ohne_werkzeuge_unterstuetzung_zweiter_versuch_bleibt_bei_api_chat(monkeypatch):
    """Der Wiederholungsversuch ohne tools (Modell kann keine Werkzeuge) muss dasselbe Ziel benutzen."""
    calls: list[dict] = []

    async def fake_acompletion(**kwargs):
        calls.append(dict(kwargs))
        if kwargs.get("tools"):
            raise Exception("registry.ollama.ai/library/x does not support tools")
        return _resp()

    import litellm
    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    tools = [{"name": "t", "description": "d", "input_schema": {"type": "object", "properties": {}}}]
    asyncio.run(backends.litellm_call(model="ollama/x", system_prompt="s", messages=[{"role": "user", "content": "hi"}],
                                      tools=tools, temperature=0.0, max_tokens=50))
    assert [c["model"] for c in calls] == ["ollama_chat/x", "ollama_chat/x"]
    assert "tools" not in calls[-1]
