from __future__ import annotations

import pytest

from hydrahive.llm import catalog


@pytest.fixture(autouse=True)
def _clear_catalog_cache():
    """Isolation: der modulglobale catalog._cache darf nicht in andere Test-Module
    leaken (sonst sieht validate_model dort eine nicht-leere Modell-Liste)."""
    catalog._cache_clear()
    yield
    catalog._cache_clear()


_OPENROUTER_RESPONSE = {
    "data": [
        {"id": "meta-llama/llama-3.3-70b-instruct:free",
         "context_length": 131072,
         "pricing": {"prompt": "0", "completion": "0"}},
        {"id": "anthropic/claude-sonnet-4-6",
         "context_length": 200000,
         "pricing": {"prompt": "0.000003", "completion": "0.000015"}},
    ]
}


def test_parse_models_marks_free_and_paid():
    entries = catalog._parse_models_response("openrouter", _OPENROUTER_RESPONSE)
    by_id = {e["id"]: e for e in entries}
    free = by_id["openrouter/meta-llama/llama-3.3-70b-instruct:free"]
    paid = by_id["openrouter/anthropic/claude-sonnet-4-6"]
    assert free["is_free"] is True
    assert free["context_window"] == 131072
    assert paid["is_free"] is False
    assert paid["price_prompt"] == "0.000003"


def test_parse_models_without_pricing_is_free_none():
    entries = catalog._parse_models_response("openai", {"data": [{"id": "gpt-4o"}]})
    assert entries[0]["id"] == "openai/gpt-4o"
    assert entries[0]["is_free"] is None
    assert entries[0]["context_window"] is None


_MODALITY_RESPONSE = {
    "data": [
        {"id": "openai/gpt-5-image-mini",
         "architecture": {"input_modalities": ["text", "image"],
                          "output_modalities": ["image", "text"]}},
        {"id": "google/lyria-3-pro-preview",
         "architecture": {"input_modalities": ["text"],
                          "output_modalities": ["audio", "text"]}},
        {"id": "anthropic/claude-sonnet-4-6"},  # ohne architecture
    ]
}


def test_parse_models_captures_modalities():
    entries = catalog._parse_models_response("openrouter", _MODALITY_RESPONSE)
    by_id = {e["id"]: e for e in entries}
    img = by_id["openrouter/openai/gpt-5-image-mini"]
    music = by_id["openrouter/google/lyria-3-pro-preview"]
    plain = by_id["openrouter/anthropic/claude-sonnet-4-6"]
    assert img["output_modalities"] == ["image", "text"]
    assert img["input_modalities"] == ["text", "image"]
    assert music["output_modalities"] == ["audio", "text"]
    assert plain["output_modalities"] == []  # kein architecture → leere Liste
    assert plain["input_modalities"] == []


def test_minimax_embedding_gets_canonical_provider_prefix():
    enriched = catalog._enrich("minimax", {"id": "embo-01"})
    assert enriched["id"] == "minimax/embo-01"
    assert enriched["category"] == "embed"


def test_enrich_passes_modalities_through():
    entry = {"id": "openrouter/openai/gpt-5-image-mini",
             "output_modalities": ["image", "text"], "input_modalities": ["text"]}
    enriched = catalog._enrich("openrouter", entry)
    assert enriched["output_modalities"] == ["image", "text"]
    assert enriched["input_modalities"] == ["text"]


def test_anthropic_endpoint_uses_x_api_key():
    from hydrahive.llm._catalog_data import PROVIDER_ENDPOINTS
    ep = PROVIDER_ENDPOINTS["anthropic"]
    assert ep["url"] == "https://api.anthropic.com/v1/models"
    assert ep["auth"] == "x-api-key"


def test_auth_for_x_api_key():
    headers, params = catalog._auth_for({"auth": "x-api-key"}, "sk-ant-api03-xxx")
    assert headers["x-api-key"] == "sk-ant-api03-xxx"
    assert "Authorization" not in headers
    assert headers["anthropic-version"] == "2023-06-01"
    assert params == {}


def test_auth_for_anthropic_oauth_uses_bearer_and_cli_headers():
    headers, params = catalog._auth_for({"auth": "x-api-key"}, "sk-ant-oat01-xxx")
    assert headers["Authorization"] == "Bearer sk-ant-oat01-xxx"
    assert "x-api-key" not in headers
    assert headers["anthropic-version"] == "2023-06-01"
    assert "oauth-2025-04-20" in headers["anthropic-beta"]
    assert headers["x-app"] == "cli"
    assert params == {}


def test_opus_5_is_complete_static_fallback():
    from hydrahive.llm._catalog_data import METADATA, STATIC_MODELS

    assert "claude-opus-5" in STATIC_MODELS["anthropic"]
    assert METADATA["claude-opus-5"] == {
        "context_window": 1_000_000,
        "tool_use": True,
        "category": "chat",
        "family": "anthropic",
    }


import asyncio


def test_anthropic_catalog_prefers_oauth_access_over_api_key(monkeypatch):
    seen = []

    async def fake_fetch(provider_id, key):
        seen.append((provider_id, key))
        return [{"id": "claude-opus-5", "context_window": 1_000_000,
                 "is_free": None, "price_prompt": None, "price_completion": None}]

    monkeypatch.setattr(catalog, "_cached_fetch", fake_fetch)
    providers = [{
        "id": "anthropic",
        "api_key": "sk-ant-api03-old",
        "oauth": {"access": "sk-ant-oat01-current"},
    }]

    result = asyncio.run(catalog.catalog_for_providers(providers))

    assert seen == [("anthropic", "sk-ant-oat01-current")]
    assert result[0]["models"][0]["id"] == "claude-opus-5"


def test_anthropic_catalog_uses_api_key_when_oauth_is_expired(monkeypatch):
    seen = []

    async def fake_fetch(provider_id, key):
        seen.append((provider_id, key))
        return [{"id": "claude-opus-5", "context_window": 1_000_000,
                 "is_free": None, "price_prompt": None, "price_completion": None}]

    monkeypatch.setattr(catalog, "_cached_fetch", fake_fetch)
    providers = [{
        "id": "anthropic",
        "api_key": "sk-ant-api03-current",
        "oauth": {"access": "sk-ant-oat01-expired", "expires_at": 1},
    }]

    asyncio.run(catalog.catalog_for_providers(providers))

    assert seen == [("anthropic", "sk-ant-api03-current")]


def test_anthropic_catalog_retries_api_key_after_oauth_failure(monkeypatch):
    seen = []

    async def fake_fetch(provider_id, key):
        seen.append((provider_id, key))
        if key.startswith("sk-ant-oat"):
            return []
        return [{"id": "claude-opus-5", "context_window": 1_000_000,
                 "is_free": None, "price_prompt": None, "price_completion": None}]

    monkeypatch.setattr(catalog, "_cached_fetch", fake_fetch)
    providers = [{
        "id": "anthropic",
        "api_key": "sk-ant-api03-fallback",
        "oauth": {"access": "sk-ant-oat01-revoked", "expires_at": 9_999_999_999},
    }]

    result = asyncio.run(catalog.catalog_for_providers(providers))

    assert seen == [
        ("anthropic", "sk-ant-oat01-revoked"),
        ("anthropic", "sk-ant-api03-fallback"),
    ]
    assert result[0]["models"][0]["id"] == "claude-opus-5"


def test_cache_is_scoped_by_credential_without_storing_raw_token(monkeypatch):
    calls = []

    async def fake_fetch(pid, key):
        calls.append((pid, key))
        return [{"id": f"{pid}/x", "context_window": None, "is_free": True,
                 "price_prompt": "0", "price_completion": "0"}]

    monkeypatch.setattr(catalog, "_fetch_live_models", fake_fetch)
    catalog._cache_clear()
    asyncio.run(catalog._cached_fetch("openrouter", "first-secret-token"))
    asyncio.run(catalog._cached_fetch("openrouter", "second-secret-token"))

    assert len(calls) == 2
    assert "first-secret-token" not in repr(catalog._cache)
    assert "second-secret-token" not in repr(catalog._cache)


def test_cache_hit_skips_second_fetch(monkeypatch):
    calls = {"n": 0}

    async def fake_fetch(pid, key):
        calls["n"] += 1
        return [{"id": "openrouter/x", "context_window": None, "is_free": True,
                 "price_prompt": "0", "price_completion": "0"}]

    monkeypatch.setattr(catalog, "_fetch_live_models", fake_fetch)
    catalog._cache_clear()
    providers = [{"id": "openrouter", "api_key": "k"}]
    asyncio.run(catalog.catalog_for_providers(providers))
    asyncio.run(catalog.catalog_for_providers(providers))
    assert calls["n"] == 1  # zweiter Aufruf aus Cache
