"""Zentrale Media-Modell-Verwaltung — ein Modell pro Media-Kategorie.

Erweitert das `default_model`/`embed_model`-Muster aus `llm.json`: das aktive
Modell pro Kategorie steht unter `media_models.{image,music,tts,transcribe,video}`.
Tools lesen es über `get_media_model(cat)`; der Tool-Parameter `model`
überschreibt weiterhin pro Aufruf.

Die Auswahl-Liste pro Kategorie kommt live aus dem Katalog, gefiltert nach
Output-/Input-Modalität (`candidates`). Musik und TTS teilen sich Audio-Output —
die Kategorie filtert nur auf audio-fähige Modelle, die Wahl trifft der Mensch.
"""
from __future__ import annotations

import time

import httpx

from hydrahive.llm._config import openrouter_key

_OPENROUTER_PREFIX = "openrouter/"
_SPEECH_MODELS_URL = "https://openrouter.ai/api/v1/models?output_modalities=speech"
_SPEECH_TTL = 300.0

# Fallback wenn llm.json keinen Eintrag hat.
# tts = echtes Speech-Modell (/audio/speech), NICHT gpt-audio (Konversation).
DEFAULTS: dict[str, str] = {
    "image": "openai/gpt-5-image-mini",
    "music": "google/lyria-3-pro-preview",
    "tts": "hexgrad/kokoro-82m",
}

# Kategorie → (Modalitäts-Seite, geforderte Modalität) für candidates() gegen den
# Chat-Katalog. tts läuft NICHT hierüber — Speech-Modelle liegen auf einer eigenen
# Fläche (list_speech_models), genau wie Video auf /videos.
_CATEGORY_MODALITY: dict[str, tuple[str, str]] = {
    "image": ("output", "image"),
    "music": ("output", "audio"),
    "transcribe": ("input", "audio"),
}

_speech_cache: tuple[float, list[dict]] | None = None


def _speech_cache_clear() -> None:
    global _speech_cache
    _speech_cache = None


def get_media_model(category: str, config: dict | None = None) -> str:
    """Aktives Modell für die Kategorie (nackter OpenRouter-Slug fürs Tool).

    Liest `media_models[category]` aus der Config, Fallback = DEFAULTS. Ein
    führendes `openrouter/` (so listet der Katalog) wird entfernt — das Tool
    spricht den OpenRouter-Endpoint direkt mit dem nackten Slug an.
    """
    if config is None:
        from hydrahive.llm._config import load_config
        config = load_config()
    chosen = ((config.get("media_models") or {}).get(category) or "").strip()
    model = chosen or DEFAULTS.get(category, "")
    if model.startswith(_OPENROUTER_PREFIX):
        model = model[len(_OPENROUTER_PREFIX):]
    return model


def candidates(category: str, catalog_entries: list[dict]) -> list[dict]:
    """Katalog-Einträge, deren Modalität zur Kategorie passt."""
    spec = _CATEGORY_MODALITY.get(category)
    if not spec:
        return []
    side, modality = spec
    key = "output_modalities" if side == "output" else "input_modalities"
    return [e for e in catalog_entries if modality in (e.get(key) or [])]


async def list_speech_models(force: bool = False) -> list[dict]:
    """Live-Liste der TTS-Modelle (output_modalities=speech) mit ihren Voices.

    OpenRouters Speech-Modelle stehen NICHT im chat-/models — eigene Fläche.
    Jeder Eintrag trägt `supported_voices`. 5-Min-Cache. Ohne Key → [].
    Gibt [{"id": str, "voices": list[str]}] zurück.
    """
    global _speech_cache
    now = time.time()
    if not force and _speech_cache and now - _speech_cache[0] < _SPEECH_TTL:
        return _speech_cache[1]
    key = openrouter_key()
    if not key:
        return []
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(_SPEECH_MODELS_URL, headers={"Authorization": f"Bearer {key}"})
        resp.raise_for_status()
        data = resp.json().get("data", [])
    out = [
        {"id": m.get("id", ""), "voices": m.get("supported_voices") or []}
        for m in data if m.get("id")
    ]
    _speech_cache = (now, out)
    return out


async def voices_for(model: str) -> list[str]:
    """Unterstützte Voices eines Speech-Modells (leer wenn unbekannt/Provider down)."""
    for m in await list_speech_models():
        if m["id"] == model:
            return list(m["voices"])
    return []


async def first_voice(model: str) -> str | None:
    """Erste unterstützte Voice eines Speech-Modells (für Tool-Default), sonst None."""
    voices = await voices_for(model)
    return voices[0] if voices else None
