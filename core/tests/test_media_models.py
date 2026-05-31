"""A2: zentrale Media-Modell-Verwaltung (llm/media_models.py).

get_media_model(cat) liest llm.json:media_models[cat], Fallback = Default.
candidates(cat, katalog) filtert Live-Katalog-Einträge nach Output-/Input-
Modalität (image→output image, music/tts→output audio, transcribe→input audio).
"""
from __future__ import annotations

from hydrahive.llm import media_models as mm


# ---------------------------------------------------------------- get_media_model

def test_default_wenn_nicht_konfiguriert():
    assert mm.get_media_model("image", {}) == "openai/gpt-5-image-mini"
    assert mm.get_media_model("music", {}) == "google/lyria-3-pro-preview"
    assert mm.get_media_model("tts", {}) == "openai/gpt-audio"


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


def test_candidates_music_und_tts_sind_audio_output():
    music = {e["id"] for e in mm.candidates("music", _CATALOG)}
    tts = {e["id"] for e in mm.candidates("tts", _CATALOG)}
    expected = {"openrouter/google/lyria-3-pro-preview", "openrouter/openai/gpt-audio"}
    assert music == expected
    assert tts == expected


def test_candidates_transcribe_nach_input_audio():
    ids = [e["id"] for e in mm.candidates("transcribe", _CATALOG)]
    assert ids == ["openrouter/openai/gpt-audio"]


def test_candidates_unbekannte_kategorie_leer():
    assert mm.candidates("voodoo", _CATALOG) == []
