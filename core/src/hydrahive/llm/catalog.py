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
from typing import Any

import httpx

from hydrahive.llm._catalog_data import (
    METADATA,
    PROVIDER_ENDPOINTS,
    PROVIDER_PREFIX,
    STATIC_MODELS,
)

logger = logging.getLogger(__name__)


def _normalize_id(provider_id: str, raw_id: str) -> str:
    """Live-API gibt 'meta/llama-...' — wir schreiben 'nvidia_nim/meta/llama-...'."""
    prefix = PROVIDER_PREFIX.get(provider_id, "")
    if prefix and not raw_id.startswith(prefix):
        return prefix + raw_id
    return raw_id


async def _fetch_live_models(provider_id: str, api_key: str) -> list[str]:
    """Holt die Modell-Liste live vom Provider. Bei Fehler: leere Liste, Warning."""
    cfg = PROVIDER_ENDPOINTS.get(provider_id, {})
    url = cfg.get("url")
    if not url or not api_key:
        return list(STATIC_MODELS.get(provider_id, []))
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if cfg["auth"] == "bearer":
                resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
            else:  # query
                param = cfg.get("query_param", "key")
                resp = await client.get(url, params={param: api_key})
            resp.raise_for_status()
            data = resp.json()
        # OpenAI/NVIDIA/Mistral/Groq: {"data": [{"id": ...}]}
        # Gemini: {"models": [{"name": "models/..."}]}
        if isinstance(data.get("data"), list):
            ids = [m.get("id", "") for m in data["data"] if m.get("id")]
        elif isinstance(data.get("models"), list):
            ids = [m.get("name", "").replace("models/", "") for m in data["models"] if m.get("name")]
        else:
            ids = []
        # Provider-Prefix + dedup
        normalized = sorted({_normalize_id(provider_id, i) for i in ids if i})
        return normalized
    except Exception as e:
        logger.warning("Catalog: live-fetch für %s fehlgeschlagen: %s", provider_id, e)
        return []


def _enrich(provider_id: str, model_id: str) -> dict[str, Any]:
    """Joint Modell-ID mit Metadata. Unbekannt → unknown:True."""
    md = METADATA.get(model_id)
    if md:
        return {"id": model_id, **md, "unknown": False}
    return {
        "id": model_id,
        "context_window": None,
        "tool_use": None,
        "category": "chat",
        "family": "?",
        "unknown": True,
    }


async def catalog_for_providers(providers: list[dict]) -> list[dict]:
    """Erzeugt Catalog-Einträge pro konfiguriertem Provider parallel.

    `providers` ist die Liste aus llm.json (jeweils {id, api_key, oauth, ...}).
    """
    async def one(p: dict) -> dict:
        pid = p.get("id", "")
        key = p.get("api_key", "") or (p.get("oauth") or {}).get("access", "")
        ids = await _fetch_live_models(pid, key)
        if not ids:
            ids = list(STATIC_MODELS.get(pid, []))
        models = [_enrich(pid, mid) for mid in ids]
        return {
            "provider_id": pid,
            "provider_name": p.get("name", pid),
            "configured": bool(key),
            "models": models,
            "live_count": len(ids),
        }
    return await asyncio.gather(*[one(p) for p in providers])
