"""A2: zentrale Media-Modell-Verwaltung (llm/media_models.py).

get_media_model(cat) liest llm.json:media_models[cat], Fallback = Default.
candidates(cat, katalog) filtert Live-Katalog-Einträge nach Output-/Input-
Modalität (image→output image, music/tts→output audio, transcribe→input audio).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hydrahive.llm import media_models as mm


# ---------------------------------------------------------------- get_media_model

def test_default_wenn_nicht_konfiguriert():
    assert mm.get_media_model("image", {}) == "openai/gpt-5-image-mini"
    assert mm.get_media_model("music", {}) == "google/lyria-3-pro-preview"
    # TTS-Default ist ein ECHTES Speech-Modell (/audio/speech), nicht gpt-audio (Konversation)
    assert mm.get_media_model("tts", {}) == "hexgrad/kokoro-82m"


def test_config_wert_hat_vorrang():
    cfg = {"media_models": {"image": "google/gemini-3-pro-image-preview"}}
    assert mm.get_media_model("image", cfg) == "google/gemini-3-pro-image-preview"


def test_leerer_config_wert_faellt_auf_default():
    cfg = {"media_models": {"image": "  "}}
    assert mm.get_media_model("image", cfg) == "openai/gpt-5-image-mini"


def test_openrouter_prefix_wird_entfernt():
    """Katalog-IDs sind 'openrouter/…' — das Tool braucht den nackten Slug."""
    cfg = {"media_models": {"music": "openrouter/google/lyria-3-pro-preview"}}
    assert mm.get_media_model("music", cfg) == "google/lyria-3-pro-preview"


def test_unbekannte_kategorie_leer():
    assert mm.get_media_model("voodoo", {}) == ""


# ---------------------------------------------------------------- candidates

_CATALOG = [
    {"id": "openrouter/openai/gpt-5-image-mini",
     "output_modalities": ["image", "text"], "input_modalities": ["text", "image"]},
    {"id": "openrouter/google/lyria-3-pro-preview",
     "output_modalities": ["audio", "text"], "input_modalities": ["text"]},
    {"id": "openrouter/openai/gpt-audio",
     "output_modalities": ["audio", "text"], "input_modalities": ["text", "audio"]},
    {"id": "openrouter/anthropic/claude-sonnet-4-6",
     "output_modalities": ["text"], "input_modalities": ["text", "image"]},
]


def test_candidates_image_nur_output_image():
    ids = [e["id"] for e in mm.candidates("image", _CATALOG)]
    assert ids == ["openrouter/openai/gpt-5-image-mini"]


def test_candidates_music_nur_audio_output():
    # Musik = output:audio (Lyria). gpt-audio ist auch audio-output, das ist ok —
    # der Mensch waehlt. TTS laeuft NICHT ueber candidates (eigene Speech-Quelle).
    music = {e["id"] for e in mm.candidates("music", _CATALOG)}
    assert "openrouter/google/lyria-3-pro-preview" in music
    assert "openrouter/anthropic/claude-sonnet-4-6" not in music


def test_candidates_unbekannte_kategorie_leer():
    assert mm.candidates("voodoo", _CATALOG) == []


# ---------------------------------------------------------------- Speech-Modelle (/audio/speech)

_SPEECH_RESPONSE = {
    "data": [
        {"id": "hexgrad/kokoro-82m", "supported_voices": ["af_bella", "am_adam"]},
        {"id": "openai/gpt-4o-mini-tts-2025-12-15", "supported_voices": ["alloy", "nova"]},
        {"id": "", "supported_voices": ["x"]},  # ohne id → ignoriert
    ]
}


def _speech_client():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=_SPEECH_RESPONSE)
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(return_value=resp)
    return client


@pytest.mark.asyncio
async def test_list_speech_models_parst_id_und_voices():
    mm._speech_cache_clear()
    with (
        patch("hydrahive.llm.media_models.httpx.AsyncClient", return_value=_speech_client()),
        patch("hydrahive.llm.media_models.openrouter_key", return_value="sk-or-v1-test"),
    ):
        models = await mm.list_speech_models(force=True)
    by_id = {m["id"]: m for m in models}
    assert by_id["hexgrad/kokoro-82m"]["voices"] == ["af_bella", "am_adam"]
    assert "" not in by_id  # leere id raus


@pytest.mark.asyncio
async def test_list_speech_models_leer_ohne_key():
    mm._speech_cache_clear()
    with patch("hydrahive.llm.media_models.openrouter_key", return_value=""):
        assert await mm.list_speech_models(force=True) == []


@pytest.mark.asyncio
async def test_first_voice_gibt_erste_voice():
    mm._speech_cache_clear()
    with (
        patch("hydrahive.llm.media_models.httpx.AsyncClient", return_value=_speech_client()),
        patch("hydrahive.llm.media_models.openrouter_key", return_value="sk-or-v1-test"),
    ):
        assert await mm.first_voice("hexgrad/kokoro-82m") == "af_bella"
        assert await mm.first_voice("unbekannt/modell") is None
