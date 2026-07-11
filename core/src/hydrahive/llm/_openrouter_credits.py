"""OpenRouter Credit-Guthaben — `GET /api/v1/credits`.

Liefert total_credits + total_usage. Das Frontend zeigt daraus Restguthaben
($ und Balken) in der Cockpit-Verbrauchsbox.

30s In-Module-Cache verhindert API-Spam beim Cockpit-Polling.
Bei fehlendem Key / Fehler: {available: False, reason: ...} — die UI blendet
die Zeile dann komplett aus.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from hydrahive.llm._config import openrouter_key

logger = logging.getLogger(__name__)


_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}
_CACHE_TTL = 30.0

_CREDITS_URL = "https://openrouter.ai/api/v1/credits"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _set_cache(data: dict) -> dict:
    global _cache
    _cache = {"data": data, "fetched_at": time.time()}
    return data


async def fetch_credits() -> dict:
    """Cached OpenRouter-Guthaben-Abfrage.

    Erfolg: {available: True, total, used, remaining, used_pct, fetched_at}
    Fehler/no-key: {available: False, reason: ...}
    """
    if _cache["data"] is not None and (time.time() - _cache["fetched_at"]) < _CACHE_TTL:
        return _cache["data"]

    key = openrouter_key()
    if not key:
        return _set_cache({"available": False, "reason": "no_api_key", "fetched_at": _iso_now()})

    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_CREDITS_URL, headers={"Authorization": f"Bearer {key}"})
    except Exception as exc:
        logger.warning("openrouter_credits HTTP fetch failed: %s", exc)
        return _set_cache({"available": False, "reason": "network_error", "fetched_at": _iso_now()})

    if resp.status_code == 401:
        return _set_cache({"available": False, "reason": "invalid_api_key", "fetched_at": _iso_now()})
    if resp.status_code >= 400:
        return _set_cache({"available": False, "reason": f"http_{resp.status_code}", "fetched_at": _iso_now()})

    try:
        raw = resp.json()
    except ValueError:
        return _set_cache({"available": False, "reason": "invalid_json", "fetched_at": _iso_now()})

    data = raw.get("data") if isinstance(raw, dict) else None
    if not isinstance(data, dict):
        return _set_cache({"available": False, "reason": "invalid_json", "fetched_at": _iso_now()})

    try:
        total = float(data.get("total_credits") or 0)
        used = float(data.get("total_usage") or 0)
    except (TypeError, ValueError):
        return _set_cache({"available": False, "reason": "invalid_json", "fetched_at": _iso_now()})

    remaining = round(total - used, 4)
    used_pct = round(used / total * 100, 1) if total > 0 else 0.0
    return _set_cache({
        "available": True,
        "fetched_at": _iso_now(),
        "total": round(total, 4),
        "used": round(used, 4),
        "remaining": remaining,
        "used_pct": min(used_pct, 100.0),
    })
