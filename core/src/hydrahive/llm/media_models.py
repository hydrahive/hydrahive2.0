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

_OPENROUTER_PREFIX = "openrouter/"

# Fallback wenn llm.json keinen Eintrag hat — die bisher in den Tools
# hartcodierten Defaults (nackte OpenRouter-Slugs).
DEFAULTS: dict[str, str] = {
    "image": "openai/gpt-5-image-mini",
    "music": "google/lyria-3-pro-preview",
    "tts": "openai/gpt-audio",
}

# Kategorie → (Modalitäts-Seite, geforderte Modalität).
_CATEGORY_MODALITY: dict[str, tuple[str, str]] = {
    "image": ("output", "image"),
    "music": ("output", "audio"),
    "tts": ("output", "audio"),
    "transcribe": ("input", "audio"),
}


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
