"""Kanonische Modell-Registry — die EINE Quelle für alle Modell-Listen + Validierung.

Aggregiert die heutigen Fetcher (catalog/media/embed) intern, klassifiziert jedes
Modell in eine Zweck-Menge und cached. async build/list, sync is_known (für validate).
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from hydrahive.llm._config import load_config
from hydrahive.llm.catalog import catalog_for_providers
from hydrahive.llm import embed as _embed
from hydrahive.llm.media_models import (
    list_speech_models, list_transcribe_models, list_video_models,
)

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


# ---------------------------------------------------------------------------
# Build + Cache
# ---------------------------------------------------------------------------

_CACHE_TTL = 300.0
_cache: tuple[float, list[ModelEntry]] | None = None
_lock = asyncio.Lock()


def _providers() -> list[dict]:
    return load_config().get("providers", [])


def _embed_models() -> list[dict]:
    return _embed.available_for_config(load_config())


def _add(acc: dict[str, ModelEntry], entry: ModelEntry) -> None:
    """Dedupliziert per id; vereinigt Zweck-Mengen (multimodal)."""
    prev = acc.get(entry.id)
    if prev is None:
        acc[entry.id] = entry
    else:
        acc[entry.id] = ModelEntry(
            id=prev.id, provider=prev.provider, label=prev.label,
            purposes=prev.purposes | entry.purposes,
            context_window=prev.context_window or entry.context_window,
            is_free=prev.is_free if prev.is_free is not None else entry.is_free,
            embed_dim=prev.embed_dim or entry.embed_dim,
            source=prev.source,
        )


async def _build() -> tuple[list[ModelEntry], bool]:
    """Baut die kanonische Modell-Liste. Gibt (modelle, complete) zurück.

    `complete` ist False, wenn ein konfigurierter Chat-Provider 0 Modelle
    beisteuerte (transienter Live-Fetch-Fehler ohne STATIC-Fallback, z.B.
    openai/openrouter). Eine unvollständige Liste darf NICHT gecacht werden —
    sonst hängt für die Cache-TTL eine Rumpf-Auswahl in allen Pickern
    (Bug: „Neues Projekt" zeigte nur 5-6 Modelle).
    """
    acc: dict[str, ModelEntry] = {}
    providers = _providers()
    complete = True
    try:
        cat = await catalog_for_providers(providers)
        for prov in cat:
            n_before = len(acc)
            for m in prov.get("models", []):
                mid = m.get("id", "")
                if not mid:
                    continue
                _add(acc, ModelEntry(
                    id=mid, provider=prov.get("provider_id", ""), label=mid,
                    purposes=_classify_catalog_entry(m),
                    context_window=m.get("context_window"), is_free=m.get("is_free"),
                    source="live" if prov.get("live_count") else "fallback",
                ))
            # Ein konfigurierter Provider, der KEIN einziges Modell beitrug, gilt
            # als (transient) fehlgeschlagen -> Build ist unvollständig.
            if len(acc) == n_before and not prov.get("models"):
                complete = False
                logger.warning(
                    "Registry: Provider %s lieferte 0 Modelle — Build unvollständig, "
                    "wird nicht gecacht (Retry beim nächsten Aufruf).",
                    prov.get("provider_id", "?"),
                )
    except Exception as e:
        logger.warning("Registry: Chat-Katalog-Build fehlgeschlagen: %s", e)
        complete = False
    try:
        for em in _embed_models():
            _add(acc, ModelEntry(id=em["model"], provider=em.get("provider", ""),
                                 label=em["model"], purposes=frozenset({"embed"}),
                                 embed_dim=em.get("dim")))
    except Exception as e:
        logger.warning("Registry: Embed-Build fehlgeschlagen: %s", e)

    async def _modality(fetch, purpose: str) -> None:
        try:
            for m in await fetch():
                mid = m.get("id", "")
                if mid:
                    _add(acc, ModelEntry(id=mid, provider="openrouter", label=mid,
                                         purposes=frozenset({purpose})))
        except Exception as e:
            logger.warning("Registry: %s-Build fehlgeschlagen: %s", purpose, e)

    await _modality(list_speech_models, "tts")
    await _modality(list_transcribe_models, "stt")
    await _modality(list_video_models, "video")
    return sorted(acc.values(), key=lambda e: (e.provider, e.label)), complete


async def list_models(modality: str | None = None) -> list[ModelEntry]:
    """Kanonische Liste (gebaut+gecached), bei modality gefiltert, sortiert."""
    global _cache
    now = time.monotonic()
    if _cache is None or now - _cache[0] >= _CACHE_TTL:
        async with _lock:
            if _cache is None or time.monotonic() - _cache[0] >= _CACHE_TTL:
                built, complete = await _build()
                # Nur eine VOLLSTÄNDIGE, nicht-leere Liste cachen. Eine Teil-Liste
                # (ein Provider transient leer) würde sonst für die Cache-TTL in
                # allen Pickern hängen — genau der „nur 5-6 Modelle"-Bug.
                if built and complete:
                    _cache = (time.monotonic(), built)
                else:
                    _cache = None
                models = built
                if modality:
                    models = [m for m in models if modality in m.purposes]
                return models
    models = _cache[1]
    if modality:
        models = [m for m in models if modality in m.purposes]
    return models


def known_ids() -> set[str]:
    """Sync: alle bekannten IDs aus dem Cache (kein Fetch — für validate)."""
    return {m.id for m in _cache[1]} if _cache else set()


def is_known(model_id: str) -> bool:
    """Sync: True wenn bekannt ODER Cache leer (Failopen wie heute)."""
    ids = known_ids()
    return (not ids) or (model_id in ids)


async def awarm() -> None:
    """Cache vorwärmen (Lifespan-Start) — Picker nie kalt nach Neustart."""
    try:
        await list_models()
    except Exception as e:
        logger.warning("Registry: awarm fehlgeschlagen: %s", e)


def invalidate() -> None:
    global _cache, _lock
    _cache = None
    _lock = asyncio.Lock()
