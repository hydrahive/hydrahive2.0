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
_TRANSCRIBE_MODELS_URL = "https://openrouter.ai/api/v1/models?input_modalities=audio"
_TRANSCRIBE_TTL = 300.0
_VIDEO_MODELS_URL = "https://openrouter.ai/api/v1/videos/models"
_VIDEO_TTL = 300.0
_IMAGE_MODELS_URL = "https://openrouter.ai/api/v1/images/models"
_IMAGE_TTL = 300.0
_AUDIO_MODELS_URL = "https://openrouter.ai/api/v1/models?output_modalities=audio"
_AUDIO_TTL = 300.0

# Fallback wenn llm.json keinen Eintrag hat.
# tts = echtes Speech-Modell (/audio/speech), NICHT gpt-audio (Konversation).
# transcribe = Whisper large-v3 (bestes offenes Transkriptions-Modell auf OpenRouter).
# video = Kling v2 (gutes Preis/Leistung-Verhältnis, schnell ~15-30s).
DEFAULTS: dict[str, str] = {
    "image": "openai/gpt-5-image-mini",
    "music": "google/lyria-3-pro-preview",
    "tts": "hexgrad/kokoro-82m",
    "transcribe": "openai/whisper-large-v3",
    "video": "kling/kling-video-v2-master",
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
_transcribe_cache: tuple[float, list[dict]] | None = None
_video_cache: tuple[float, list[dict]] | None = None
_image_cache: tuple[float, list[dict]] | None = None
_audio_cache: tuple[float, list[dict]] | None = None


def _speech_cache_clear() -> None:
    global _speech_cache
    _speech_cache = None


def _transcribe_cache_clear() -> None:
    global _transcribe_cache
    _transcribe_cache = None


def _video_cache_clear() -> None:
    global _video_cache
    _video_cache = None


def _image_cache_clear() -> None:
    global _image_cache
    _image_cache = None


def _audio_cache_clear() -> None:
    global _audio_cache
    _audio_cache = None


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


# Bekannte OpenRouter-Transkriptions-Modelle als Fallback wenn die API-Filterung
# leer bleibt (OpenRouter unterstützt ?input_modalities= nicht zuverlässig).
_TRANSCRIBE_FALLBACK: list[dict] = [
    {"id": "openai/whisper-large-v3", "name": "Whisper Large v3"},
    {"id": "openai/whisper-large-v3-turbo", "name": "Whisper Large v3 Turbo"},
    {"id": "openai/whisper-1", "name": "Whisper v1"},
]


async def list_transcribe_models(force: bool = False) -> list[dict]:
    """Live-Liste der Audio-Transkriptions-Modelle von OpenRouter.

    Versucht den Catalog nach input_modalities=audio zu filtern. Gibt bei leerem
    Ergebnis (OpenRouter unterstützt den Filter nicht zuverlässig) die bekannte
    Fallback-Liste zurück. Ohne Key → Fallback. 5-Min-Cache.
    Gibt [{"id": str, "name": str}] zurück.
    """
    global _transcribe_cache
    now = time.time()
    if not force and _transcribe_cache and now - _transcribe_cache[0] < _TRANSCRIBE_TTL:
        return _transcribe_cache[1]
    key = openrouter_key()
    if not key:
        return _TRANSCRIBE_FALLBACK
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                _TRANSCRIBE_MODELS_URL,
                headers={"Authorization": f"Bearer {key}"},
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
        out = [
            {"id": m.get("id", ""), "name": m.get("name") or m.get("id", "")}
            for m in data
            if m.get("id") and "audio" in (m.get("input_modalities") or [])
        ]
    except Exception:
        out = []
    if not out:
        out = _TRANSCRIBE_FALLBACK
    _transcribe_cache = (now, out)
    return out


async def list_video_models(force: bool = False) -> list[dict]:
    """Live-Liste der Video-Generierungs-Modelle von OpenRouter.

    Video-Modelle liegen auf einer eigenen Fläche (/api/v1/videos/models),
    NICHT im chat-/models. 5-Min-Cache. Ohne Key → [].
    Gibt [{"id": str, "name": str}] zurück.
    """
    global _video_cache
    now = time.time()
    if not force and _video_cache and now - _video_cache[0] < _VIDEO_TTL:
        return _video_cache[1]
    key = openrouter_key()
    if not key:
        return []
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(_VIDEO_MODELS_URL, headers={"Authorization": f"Bearer {key}"})
        resp.raise_for_status()
        data = resp.json()
    # OpenRouter gibt entweder {"data": [...]} oder direkt eine Liste
    items = data.get("data") or (data if isinstance(data, list) else [])
    out = [
        {"id": m.get("id", ""), "name": m.get("name") or m.get("id", "")}
        for m in items if m.get("id")
    ]
    _video_cache = (now, out)
    return out


async def list_image_models(force: bool = False) -> list[dict]:
    """Live-Liste der Bild-Generierungs-Modelle von OpenRouter.

    Eigene Fläche /api/v1/images/models (mehr als der Modalitäts-Filter im
    chat-/models). 5-Min-Cache. Ohne Key → []. Gibt [{"id", "name"}] zurück.
    """
    global _image_cache
    now = time.time()
    if not force and _image_cache and now - _image_cache[0] < _IMAGE_TTL:
        return _image_cache[1]
    key = openrouter_key()
    if not key:
        return []
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(_IMAGE_MODELS_URL, headers={"Authorization": f"Bearer {key}"})
        resp.raise_for_status()
        data = resp.json()
    items = data.get("data") or (data if isinstance(data, list) else [])
    out = [
        {"id": m.get("id", ""), "name": m.get("name") or m.get("id", "")}
        for m in items if m.get("id")
    ]
    _image_cache = (now, out)
    return out


async def list_audio_models(force: bool = False) -> list[dict]:
    """Live-Liste der Audio-Ausgabe-Modelle (Musik/Sprache) von OpenRouter.

    Audio-Modelle liegen NICHT auf einer eigenen Fläche — sie stehen im
    zentralen /models, gefiltert nach output_modalities=audio (z.B. Lyria,
    gpt-audio). 5-Min-Cache. Ohne Key → []. Gibt [{"id", "name"}] zurück.
    """
    global _audio_cache
    now = time.time()
    if not force and _audio_cache and now - _audio_cache[0] < _AUDIO_TTL:
        return _audio_cache[1]
    key = openrouter_key()
    if not key:
        return []
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(_AUDIO_MODELS_URL, headers={"Authorization": f"Bearer {key}"})
        resp.raise_for_status()
        data = resp.json().get("data", [])
    out = [
        {"id": m.get("id", ""), "name": m.get("name") or m.get("id", "")}
        for m in data
        if m.get("id") and "audio" in ((m.get("architecture") or {}).get("output_modalities") or m.get("output_modalities") or [])
    ]
    _audio_cache = (now, out)
    return out
