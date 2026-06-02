"""LLM-Modell-Catalog: Live-Listing pro Provider + interne Metadata.

Per Provider hat HH2 eine Liste der gepflegten Metadata (context_window,
tool_use, category, params, hint). Beim Catalog-Aufruf wird live von der
Provider-API die Modell-Liste geholt und mit dieser Metadata gejoint.

Modelle die live verfügbar sind aber nicht in der Metadata stehen, kommen
trotzdem in die Liste — mit `metadata.unknown=True`.

Daten (Provider-Endpoints, Static-Listen, Metadata) liegen in
`_catalog_data.py`; dieses Modul enthält nur die Logik.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from hydrahive.llm._catalog_data import (
    METADATA,
    PROVIDER_ENDPOINTS,
    PROVIDER_PREFIX,
    STATIC_MODELS,
)

logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # 5 Minuten (Hermes-Muster)
_cache: dict[str, tuple[float, list[dict]]] = {}
_cache_locks: dict[str, asyncio.Lock] = {}


def _cache_clear() -> None:
    _cache.clear()


async def _cached_fetch(provider_id: str, api_key: str) -> list[dict]:
    """Live-Fetch mit 5-Min-TTL-Cache + Lock gegen parallele Fetches."""
    now = time.monotonic()
    hit = _cache.get(provider_id)
    if hit and now - hit[0] < _CACHE_TTL:
        return hit[1]
    lock = _cache_locks.setdefault(provider_id, asyncio.Lock())
    async with lock:
        hit = _cache.get(provider_id)  # zweiter Check nach Lock
        if hit and time.monotonic() - hit[0] < _CACHE_TTL:
            return hit[1]
        entries = await _fetch_live_models(provider_id, api_key)
        if entries:  # nur erfolgreiche Fetches cachen
            _cache[provider_id] = (time.monotonic(), entries)
        return entries


def _normalize_id(provider_id: str, raw_id: str) -> str:
    """Live-API gibt 'meta/llama-...' — wir schreiben 'nvidia_nim/meta/llama-...'."""
    prefix = PROVIDER_PREFIX.get(provider_id, "")
    if prefix and not raw_id.startswith(prefix):
        return prefix + raw_id
    return raw_id


def _parse_models_response(provider_id: str, data: dict) -> list[dict]:
    """Extrahiert strukturierte Modell-Einträge aus der /v1/models-Antwort.

    OpenRouter liefert pricing (Strings) + context_length; andere Provider oft nur id.
    is_free = pricing.prompt und .completion sind beide '0'. Ohne pricing → None.
    """
    raw: list[dict]
    if isinstance(data.get("data"), list):
        raw = data["data"]
    elif isinstance(data.get("models"), list):  # Gemini
        raw = [{"id": m.get("name", "").replace("models/", "")} for m in data["models"] if m.get("name")]
    else:
        raw = []

    out: list[dict] = []
    for m in raw:
        mid = m.get("id", "")
        if not mid:
            continue
        pricing = m.get("pricing") or {}
        prompt = pricing.get("prompt")
        completion = pricing.get("completion")
        is_free: bool | None
        if prompt is None and completion is None:
            is_free = None
        else:
            is_free = (str(prompt) == "0" and str(completion) == "0")
        arch = m.get("architecture") or {}
        out.append({
            "id": _normalize_id(provider_id, mid),
            "context_window": m.get("context_length"),
            "is_free": is_free,
            "price_prompt": prompt,
            "price_completion": completion,
            "output_modalities": arch.get("output_modalities") or [],
            "input_modalities": arch.get("input_modalities") or [],
        })
    return out


def _auth_for(cfg: dict, api_key: str) -> tuple[dict, dict]:
    """Gibt (headers, params) für den Provider-Auth-Modus zurück."""
    kind = cfg.get("auth")
    if kind == "bearer":
        return {"Authorization": f"Bearer {api_key}"}, {}
    if kind == "query":
        return {}, {cfg.get("query_param", "key"): api_key}
    if kind == "x-api-key":  # Anthropic
        return {"x-api-key": api_key, "anthropic-version": "2023-06-01"}, {}
    return {}, {}


async def _fetch_live_models(provider_id: str, api_key: str) -> list[dict]:
    """Holt strukturierte Modell-Einträge live. Bei Fehler: leere Liste."""
    cfg = PROVIDER_ENDPOINTS.get(provider_id, {})
    url = cfg.get("url")
    if not url or not api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers, params = _auth_for(cfg, api_key)
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
        return _parse_models_response(provider_id, data)
    except Exception as e:
        logger.warning("Catalog: live-fetch für %s fehlgeschlagen: %s", provider_id, e)
        return []


def _enrich(provider_id: str, entry: dict) -> dict[str, Any]:
    """Joint Live-Eintrag mit METADATA. Live-context_window hat Vorrang."""
    from hydrahive.llm._anthropic import _uses_effort_param
    md = METADATA.get(entry["id"], {})
    return {
        "id": entry["id"],
        "context_window": entry.get("context_window") or md.get("context_window"),
        "tool_use": md.get("tool_use"),
        "category": md.get("category", "chat"),
        "family": md.get("family", "?"),
        "is_free": entry.get("is_free"),
        "price_prompt": entry.get("price_prompt"),
        "price_completion": entry.get("price_completion"),
        "output_modalities": entry.get("output_modalities") or [],
        "input_modalities": entry.get("input_modalities") or [],
        "supports_effort": _uses_effort_param(entry["id"]),
        "unknown": entry["id"] not in METADATA,
    }


async def catalog_for_providers(providers: list[dict]) -> list[dict]:
    """Erzeugt Catalog-Einträge pro konfiguriertem Provider parallel.

    `providers` ist die Liste aus llm.json (jeweils {id, api_key, oauth, ...}).
    """
    async def one(p: dict) -> dict:
        pid = p.get("id", "")
        key = p.get("api_key", "") or (p.get("oauth") or {}).get("access", "")
        entries = await _cached_fetch(pid, key)
        if not entries:
            entries = [{"id": _normalize_id(pid, m), "context_window": None,
                        "is_free": None, "price_prompt": None, "price_completion": None}
                       for m in STATIC_MODELS.get(pid, [])]
        models = [_enrich(pid, e) for e in entries]
        return {
            "provider_id": pid,
            "provider_name": p.get("name", pid),
            "configured": bool(key),
            "models": models,
            "live_count": len(entries),
        }
    return await asyncio.gather(*[one(p) for p in providers])
