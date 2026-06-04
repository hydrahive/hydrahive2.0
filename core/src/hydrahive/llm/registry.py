"""Kanonische Modell-Registry — die EINE Quelle für alle Modell-Listen + Validierung.

Aggregiert die heutigen Fetcher (catalog/media/embed) intern, klassifiziert jedes
Modell in eine Zweck-Menge und cached. async build/list, sync is_known (für validate).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PURPOSES = ("chat", "embed", "tts", "stt", "image", "video", "music")


@dataclass(frozen=True)
class ModelEntry:
    id: str
    provider: str
    label: str
    purposes: frozenset[str]
    context_window: int | None = None
    is_free: bool | None = None
    embed_dim: int | None = None
    source: str = "live"  # "live" | "fallback"


def _classify_catalog_entry(entry: dict) -> frozenset[str]:
    """Zweck-Menge eines Chat-Katalog-Eintrags. Default chat; image/music aus output_modalities."""
    out = {"chat"}
    om = entry.get("output_modalities") or []
    if "image" in om:
        out.add("image")
    if "audio" in om:
        out.add("music")
    return frozenset(out)
