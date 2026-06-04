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
