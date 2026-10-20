"""DeepSeek als LLM-Anbieter (Spec docs/specs/deepseek-provider.md).

Offizielle Doku 20.10.2026: OpenAI-kompatibel, https://api.deepseek.com, Bearer-Schlüssel,
Modelle deepseek-flash und deepseek-v4-pro. LiteLLM-Route `deepseek/`, Schlüssel DEEPSEEK_API_KEY.
"""
from __future__ import annotations

import asyncio
import json
import os

import pytest

from hydrahive.llm import catalog


@pytest.fixture(autouse=True)
def _clear_catalog_cache():
    catalog._cache_clear()
    yield
    catalog._cache_clear()


# --- Daten an den Stellen, die jeder Anbieter braucht ---------------------------------------------

def test_key_is_mapped_and_protected():
    from hydrahive.llm._config import _ENV_MAP, provider_env_vars
    assert _ENV_MAP["deepseek"] == "DEEPSEEK_API_KEY"
    assert "DEEPSEEK_API_KEY" in provider_env_vars()          # landet damit in der shell_exec-Sperrliste


def test_apply_keys_sets_env(monkeypatch):
    from hydrahive.llm._config import apply_keys
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    apply_keys({"providers": [{"id": "deepseek", "api_key": "sk-test-deepseek"}]})
    assert os.environ["DEEPSEEK_API_KEY"] == "sk-test-deepseek"
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)


def test_catalog_endpoint_prefix_and_fallback_models():
    from hydrahive.llm._catalog_data import PROVIDER_ENDPOINTS, PROVIDER_PREFIX, STATIC_MODELS
    assert PROVIDER_ENDPOINTS["deepseek"] == {"url": "https://api.deepseek.com/models", "auth": "bearer"}
    assert PROVIDER_PREFIX["deepseek"] == "deepseek/"
    assert STATIC_MODELS["deepseek"] == ["deepseek/deepseek-flash", "deepseek/deepseek-v4-pro"]


def test_model_ids_know_the_prefix():
    from hydrahive.llm.model_ids import _PROVIDER_PREFIXES
    assert "deepseek/" in _PROVIDER_PREFIXES


def test_normalize_adds_prefix_once():
    assert catalog._normalize_id("deepseek", "deepseek-flash") == "deepseek/deepseek-flash"
    assert catalog._normalize_id("deepseek", "deepseek/deepseek-flash") == "deepseek/deepseek-flash"


# --- Katalog: live und ohne Netz -------------------------------------------------------------------

_LIVE = {"object": "list", "data": [
    {"id": "deepseek-flash", "object": "model", "owned_by": "deepseek"},
    {"id": "deepseek-v4-pro", "object": "model", "owned_by": "deepseek"},
]}


def test_catalog_uses_live_list(monkeypatch):
    calls = []

    async def fake_fetch(pid, key, **kw):
        calls.append((pid, key))
        return catalog._parse_models_response(pid, json.loads(json.dumps(_LIVE)))

    monkeypatch.setattr(catalog, "_fetch_live_models", fake_fetch)
    out = asyncio.run(catalog.catalog_for_providers([{"id": "deepseek", "name": "DeepSeek", "api_key": "sk-ds"}]))
    entry = out[0]
    assert calls == [("deepseek", "sk-ds")]
    assert entry["configured"] is True and entry["live_count"] == 2
    assert [m["id"] for m in entry["models"]] == ["deepseek/deepseek-flash", "deepseek/deepseek-v4-pro"]


def test_catalog_falls_back_without_network(monkeypatch):
    async def offline(pid, key, **kw):
        return []

    monkeypatch.setattr(catalog, "_fetch_live_models", offline)
    out = asyncio.run(catalog.catalog_for_providers([{"id": "deepseek", "name": "DeepSeek", "api_key": "sk-ds"}]))
    assert out[0]["live_count"] == 0
    assert [m["id"] for m in out[0]["models"]] == ["deepseek/deepseek-flash", "deepseek/deepseek-v4-pro"]


def test_catalog_without_key_is_not_configured(monkeypatch):
    async def never(pid, key, **kw):
        raise AssertionError("ohne Schlüssel kein Abruf")

    monkeypatch.setattr(catalog, "_fetch_live_models", never)
    out = asyncio.run(catalog.catalog_for_providers([{"id": "deepseek", "name": "DeepSeek", "api_key": ""}]))
    assert out[0]["configured"] is False


# --- Modell einem Agenten geben: Anbieter wird erkannt ---------------------------------------------

def test_use_in_agent_assigns_model_to_deepseek(tmp_path, monkeypatch):
    from hydrahive.api.routes import llm_catalog
    from hydrahive.settings import settings
    cfg = tmp_path / "llm.json"
    cfg.write_text(json.dumps({"providers": [{"id": "deepseek", "api_key": "sk-ds", "models": []},
                                             {"id": "openai", "api_key": "sk-o", "models": []}]}))
    monkeypatch.setattr(type(settings), "llm_config", property(lambda self: cfg))
    llm_catalog._ensure_model_in_providers("deepseek/deepseek-v4-pro")
    data = json.loads(cfg.read_text())
    by_id = {p["id"]: p for p in data["providers"]}
    assert by_id["deepseek"]["models"] == ["deepseek/deepseek-v4-pro"]
    assert by_id["openai"]["models"] == []
