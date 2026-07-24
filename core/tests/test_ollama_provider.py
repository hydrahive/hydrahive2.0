"""Tests für die Ollama-Provider-Unterstützung.

Ollama spricht eine OpenAI-kompatible API und läuft über den LiteLLM-Pfad.
Anders als die Cloud-Provider kommt die Base-URL aus der user-eigenen llm.json
(`api_base`), nicht aus hardcodierten PROVIDER_ENDPOINTS. Diese Tests sichern:
1. api_base wird aus der Config gelesen (provider_api_base).
2. litellm_call reicht api_base an litellm.acompletion durch.
3. Nicht-Ollama-Provider setzen kein api_base-kwarg (Regression-Schutz).
4. Catalog listet Ollama-Modelle live vom user-Endpoint.
5. Ollama gilt ohne Key als configured, wenn api_base gesetzt ist.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.llm import catalog


@pytest.fixture(autouse=True)
def _clear_catalog_cache():
    catalog._cache_clear()
    yield
    catalog._cache_clear()


# --- 1. provider_api_base() liest die api_base aus der Config ---------------

def test_provider_api_base_returns_configured_url():
    from hydrahive.llm._config import provider_api_base
    cfg = {"providers": [
        {"id": "ollama", "api_base": "http://localhost:11434"},
        {"id": "openai", "api_key": "sk-x"},
    ]}
    assert provider_api_base(cfg, "ollama") == "http://localhost:11434"


def test_provider_api_base_none_when_not_set():
    from hydrahive.llm._config import provider_api_base
    cfg = {"providers": [{"id": "openai", "api_key": "sk-x"}]}
    assert provider_api_base(cfg, "openai") is None
    assert provider_api_base(cfg, "ollama") is None


def test_ollama_in_env_map():
    from hydrahive.llm._config import provider_env_vars
    # Ollama-Key muss geschützt sein (shell_exec-Denylist speist sich hieraus).
    assert "OLLAMA_API_KEY" in provider_env_vars()


# --- 2. litellm_call reicht api_base durch ----------------------------------

def test_litellm_call_passes_api_base(monkeypatch):
    from hydrahive.runner import _llm_bridge_backends as backends

    captured: dict = {}

    class _Msg:
        content = "hi"
        tool_calls = None

    class _Choice:
        message = _Msg()
        finish_reason = "stop"

    class _Resp:
        choices = [_Choice()]
        usage = None

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return _Resp()

    import litellm
    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    asyncio.run(backends.litellm_call(
        model="ollama/llama3.1",
        system_prompt="sys",
        messages=[{"role": "user", "content": "hi"}],
        tools=[],
        temperature=0.0,
        max_tokens=100,
        api_base="http://localhost:11434",
    ))
    assert captured.get("api_base") == "http://localhost:11434"


def test_litellm_call_no_api_base_kwarg_when_none(monkeypatch):
    """Regression: Provider ohne api_base dürfen KEIN api_base-kwarg bekommen."""
    from hydrahive.runner import _llm_bridge_backends as backends

    captured: dict = {}

    class _Msg:
        content = "hi"
        tool_calls = None

    class _Choice:
        message = _Msg()
        finish_reason = "stop"

    class _Resp:
        choices = [_Choice()]
        usage = None

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return _Resp()

    import litellm
    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    asyncio.run(backends.litellm_call(
        model="openai/gpt-4o",
        system_prompt="sys",
        messages=[{"role": "user", "content": "hi"}],
        tools=[],
        temperature=0.0,
        max_tokens=100,
    ))
    assert "api_base" not in captured


# --- 3. Catalog: Ollama live vom user-Endpoint ------------------------------

def test_ollama_prefix_registered():
    from hydrahive.llm._catalog_data import PROVIDER_PREFIX
    assert PROVIDER_PREFIX.get("ollama") == "ollama/"


def test_catalog_ollama_configured_without_key(monkeypatch):
    """Ollama gilt als configured, wenn api_base gesetzt ist — auch ohne Key."""
    async def fake_fetch_ollama(provider):
        return [{"id": "ollama/llama3.1", "context_window": None, "is_free": None,
                 "price_prompt": None, "price_completion": None}]

    monkeypatch.setattr(catalog, "_fetch_ollama_models", fake_fetch_ollama, raising=False)

    providers = [{"id": "ollama", "api_base": "http://localhost:11434"}]
    result = asyncio.run(catalog.catalog_for_providers(providers))
    entry = result[0]
    assert entry["provider_id"] == "ollama"
    assert entry["configured"] is True
    assert any(m["id"] == "ollama/llama3.1" for m in entry["models"])


def test_catalog_ollama_no_api_base_empty(monkeypatch):
    """Ohne api_base: leere Modell-Liste, kein Crash."""
    providers = [{"id": "ollama"}]
    result = asyncio.run(catalog.catalog_for_providers(providers))
    entry = result[0]
    assert entry["provider_id"] == "ollama"
    assert entry["models"] == []
