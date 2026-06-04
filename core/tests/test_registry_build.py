import pytest


@pytest.fixture
def fake_sources(monkeypatch):
    from hydrahive.llm import registry

    async def fake_catalog(providers):
        return [{"provider_id": "openrouter", "provider_name": "OpenRouter", "configured": True,
                 "models": [
                    {"id": "openrouter/chatty", "context_window": 8000, "is_free": True, "output_modalities": []},
                    {"id": "openrouter/painter", "output_modalities": ["image"]},
                 ], "live_count": 2}]

    async def fake_speech(force=False): return [{"id": "hexgrad/kokoro-82m", "voices": ["af"]}]
    async def fake_transcribe(force=False): return [{"id": "openai/whisper-large-v3", "name": "Whisper"}]
    async def fake_video(force=False): return [{"id": "kling/v2", "name": "Kling"}]

    monkeypatch.setattr(registry, "catalog_for_providers", fake_catalog)
    monkeypatch.setattr(registry, "list_speech_models", fake_speech)
    monkeypatch.setattr(registry, "list_transcribe_models", fake_transcribe)
    monkeypatch.setattr(registry, "list_video_models", fake_video)
    monkeypatch.setattr(registry, "_embed_models", lambda: [{"model": "baai/bge-m3", "dim": 1024, "provider": "openrouter"}])
    monkeypatch.setattr(registry, "_providers", lambda: [{"id": "openrouter", "api_key": "k"}])
    registry.invalidate()
    return registry


@pytest.mark.asyncio
async def test_list_models_classified_and_sorted(fake_sources):
    r = fake_sources
    chat = [m.id for m in await r.list_models("chat")]
    assert "openrouter/chatty" in chat and "openrouter/painter" in chat
    assert [m.id for m in await r.list_models("image")] == ["openrouter/painter"]
    assert [m.id for m in await r.list_models("tts")] == ["hexgrad/kokoro-82m"]
    assert [m.id for m in await r.list_models("stt")] == ["openai/whisper-large-v3"]
    assert [m.id for m in await r.list_models("video")] == ["kling/v2"]
    assert [m.id for m in await r.list_models("embed")] == ["baai/bge-m3"]
    allm = await r.list_models()
    assert allm == sorted(allm, key=lambda e: (e.provider, e.label))


@pytest.mark.asyncio
async def test_is_known_reads_cache_after_build(fake_sources):
    r = fake_sources
    await r.list_models()
    assert r.is_known("openrouter/chatty") is True
    assert r.is_known("does-not-exist") is False


def test_is_known_empty_cache_is_failopen(monkeypatch):
    from hydrahive.llm import registry
    registry.invalidate()
    assert registry.is_known("anything") is True


@pytest.mark.asyncio
async def test_empty_build_not_cached(monkeypatch):
    from hydrahive.llm import registry
    async def empty_build(): return []
    monkeypatch.setattr(registry, "_build", empty_build)
    registry.invalidate()
    assert await registry.list_models() == []
    assert registry.known_ids() == set()      # nicht gecacht
    assert registry.is_known("x") is True      # failopen bei leerem Cache


@pytest.mark.asyncio
async def test_anthropic_401_static_fallback_keeps_claude_known(monkeypatch):
    """Regression (der eigentliche Bug): Anthropic-Live-Fetch schlägt fehl (401 → leer),
    catalog_for_providers liefert den STATIC_MODELS-Fallback → claude bleibt in der Registry
    + known_ids → validate würde es akzeptieren."""
    from hydrahive.llm import registry, catalog
    from hydrahive.llm._catalog_data import STATIC_MODELS
    monkeypatch.setattr(registry, "_providers", lambda: [{"id": "anthropic", "api_key": "bad-key"}])
    monkeypatch.setattr(registry, "_embed_models", lambda: [])
    async def empty_live(provider_id, api_key):   # simuliert 401 / leeren Live-Fetch
        return []
    monkeypatch.setattr(catalog, "_fetch_live_models", empty_live)
    async def none(force=False): return []
    monkeypatch.setattr(registry, "list_speech_models", none)
    monkeypatch.setattr(registry, "list_transcribe_models", none)
    monkeypatch.setattr(registry, "list_video_models", none)
    catalog._cache_clear()
    registry.invalidate()
    chat_ids = {m.id for m in await registry.list_models("chat")}
    assert any(cid in chat_ids for cid in STATIC_MODELS["anthropic"]), \
        f"claude-Fallback fehlt; got {sorted(chat_ids)}"
    assert registry.is_known(STATIC_MODELS["anthropic"][0]) is True
