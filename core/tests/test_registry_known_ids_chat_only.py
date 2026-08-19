"""Regression: known_ids() liefert nur Chat-Modelle.

Hintergrund (Frischinstallation Ubuntu 26.04, 2026-08-19): Auf einem Server
ohne konfigurierten LLM-Provider enthielt die Registry trotzdem drei fest
eingebaute STT-Modelle (openai/whisper-*). Damit war known_ids() nicht mehr
leer — und genau daran hängt der Failopen in validate_model.

Folge: Jede Agent-Erstellung schlug fehl, weil kein einziges *Chat*-Modell
bekannt war. Der Buddy-Endpunkt lieferte HTTP 500 mit
"Modell 'claude-sonnet-4-6' ist nicht in der Live-Modell-Liste verfügbar",
und die Buddy-Seite war unbenutzbar.
"""

from __future__ import annotations

import time

import pytest


@pytest.fixture
def _clean_registry():
    """Cache vor und nach dem Test zurücksetzen — sonst leaken Fake-Modelle."""
    from hydrahive.llm import registry

    before = registry._cache
    yield registry
    registry._cache = before


def _entry(registry_mod, model_id: str, purpose: str):
    return registry_mod.ModelEntry(
        id=model_id, label=model_id, provider="testprovider",
        purposes=frozenset({purpose}),
    )


def test_stt_only_cache_yields_empty_known_ids(_clean_registry):
    """Nur STT im Cache ⇒ known_ids leer ⇒ Failopen greift.

    Das ist der Zustand einer frischen Installation ohne LLM-Provider.
    """
    registry = _clean_registry
    registry._cache = (time.time(), [
        _entry(registry, "openai/whisper-1", "stt"),
        _entry(registry, "openai/whisper-large-v3", "stt"),
    ])

    assert registry.known_ids() == set()
    # Failopen: unbekanntes Modell muss durchgewunken werden, solange kein
    # einziges Chat-Modell bekannt ist.
    assert registry.is_known("irgendein-modell") is True


def test_chat_models_are_returned_and_gate_unknown(_clean_registry):
    """Sobald Chat-Modelle da sind, gilt die Liste — und schließt Fremdes aus."""
    registry = _clean_registry
    registry._cache = (time.time(), [
        _entry(registry, "openai/whisper-1", "stt"),
        _entry(registry, "anthropic/claude-test", "chat"),
    ])

    assert registry.known_ids() == {"anthropic/claude-test"}
    assert registry.is_known("anthropic/claude-test") is True
    assert registry.is_known("gibt-es-nicht") is False


def test_validate_model_passes_when_only_stt_known(_clean_registry):
    """validate_model darf auf einer frischen Instanz nicht blockieren."""
    from hydrahive.agents import _validation

    registry = _clean_registry
    registry._cache = (time.time(), [_entry(registry, "openai/whisper-1", "stt")])

    # Kein Raise erwartet — vorher flog hier AgentValidationError.
    _validation.validate_model("claude-sonnet-4-6")
