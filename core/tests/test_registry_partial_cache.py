"""Registry darf keine UNVOLLSTÄNDIGE Modell-Liste cachen.

Bug (von till gefunden): Beim „Neues Projekt"-Dialog erschienen nur 5-6 Modelle
(ein paar Claude/GPT, 1-2 OpenRouter) statt der vollen Liste — während die
Agenten-Einstellungen alle zeigten.

Root-Cause: Wenn ein konfigurierter Cloud-Provider (z.B. OpenRouter/OpenAI)
transient fehlschlägt, liefert catalog_for_providers für ihn 0 Modelle (der
STATIC-Fallback ist für openai/openrouter leer). Die restliche Teil-Liste
(z.B. nur die 9 statischen Claude-Modelle) ist aber NICHT leer -> _build gab
sie zurück und der alte Cache-Guard (`if built:`) cachte sie für 5 Minuten.
Wer in diesem Fenster einen Picker öffnete, sah die Rumpf-Liste.

Vertrag (RED): Wenn ein konfigurierter Provider 0 Modelle beisteuert, gilt der
Build als unvollständig und wird NICHT gecacht — der nächste Aufruf retryt.

Imports lazy in der Funktion (Test-Isolation).
"""
from __future__ import annotations

import asyncio


def _reset_registry():
    from hydrahive.llm import registry
    registry._cache = None
    return registry


def test_partial_catalog_is_not_cached(monkeypatch):
    registry = _reset_registry()

    providers = [
        {"id": "anthropic", "api_key": "sk-a"},
        {"id": "openrouter", "api_key": "sk-o"},
    ]
    monkeypatch.setattr(registry, "_providers", lambda: providers)
    monkeypatch.setattr(registry, "_embed_models", lambda: [])

    calls = {"n": 0}

    async def _fake_catalog(_provs):
        calls["n"] += 1
        # 1. Aufruf: openrouter transient leer (Fetch-Fehler, leerer STATIC-Fallback)
        # 2. Aufruf: openrouter liefert wieder Modelle
        if calls["n"] == 1:
            return [
                {"provider_id": "anthropic", "live_count": 9,
                 "models": [{"id": "claude-opus-4-8"}, {"id": "claude-sonnet-4-6"}]},
                {"provider_id": "openrouter", "live_count": 0, "models": []},
            ]
        return [
            {"provider_id": "anthropic", "live_count": 9,
             "models": [{"id": "claude-opus-4-8"}, {"id": "claude-sonnet-4-6"}]},
            {"provider_id": "openrouter", "live_count": 300,
             "models": [{"id": f"openrouter/m{i}"} for i in range(300)]},
        ]

    monkeypatch.setattr(registry, "catalog_for_providers", _fake_catalog)

    async def _noop():
        return []
    monkeypatch.setattr(registry, "list_speech_models", _noop)
    monkeypatch.setattr(registry, "list_transcribe_models", _noop)
    monkeypatch.setattr(registry, "list_video_models", _noop)

    # 1. Aufruf: unvollständig -> NICHT gecacht
    first = asyncio.run(registry.list_models("chat"))
    assert registry._cache is None, "Teil-Liste darf nicht gecacht werden"

    # 2. Aufruf: baut neu (kein Cache-Hit auf die Rumpf-Liste) -> jetzt vollständig
    second = asyncio.run(registry.list_models("chat"))
    assert calls["n"] == 2, "unvollständiger Build muss neu bauen statt Cache zu treffen"
    assert len(second) > len(first)
    assert len(second) >= 300


def test_complete_catalog_is_cached(monkeypatch):
    """Gegenprobe: vollständiger Build wird gecacht (kein Doppel-Fetch)."""
    registry = _reset_registry()

    providers = [{"id": "anthropic", "api_key": "sk-a"}]
    monkeypatch.setattr(registry, "_providers", lambda: providers)
    monkeypatch.setattr(registry, "_embed_models", lambda: [])

    calls = {"n": 0}

    async def _fake_catalog(_provs):
        calls["n"] += 1
        return [{"provider_id": "anthropic", "live_count": 2,
                 "models": [{"id": "claude-opus-4-8"}, {"id": "claude-sonnet-4-6"}]}]

    monkeypatch.setattr(registry, "catalog_for_providers", _fake_catalog)

    async def _noop():
        return []
    monkeypatch.setattr(registry, "list_speech_models", _noop)
    monkeypatch.setattr(registry, "list_transcribe_models", _noop)
    monkeypatch.setattr(registry, "list_video_models", _noop)

    asyncio.run(registry.list_models("chat"))
    asyncio.run(registry.list_models("chat"))
    assert calls["n"] == 1, "vollständiger Build muss gecacht werden"
    assert registry._cache is not None
