"""MiniMax Token-Plan / Usage API — `GET /v1/token_plan/remains`.

Liefert pro Modell: interval_total/used (current period) + weekly_total/used
+ reset-Zeitpunkt. Frontend zeigt das als Quota-Anzeige im Dashboard.

30s In-Module-Cache verhindert API-Spam beim Dashboard-Polling.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from hydrahive.llm._config import get_provider_key, load_config

logger = logging.getLogger(__name__)


_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}
_CACHE_TTL = 30.0


_MODEL_CATEGORIES: list[tuple[str, str]] = [
    ("MiniMax-M",      "text"),
    ("MiniMax-Hailuo", "video"),
    ("Hailuo",         "video"),
    ("speech",         "tts"),
    ("music",          "music"),
    ("image",          "image"),
]


def _short_name(model_name: str) -> str:
    for prefix, short in _MODEL_CATEGORIES:
        if model_name.startswith(prefix):
            return short
    return "misc"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_model(raw: dict) -> dict:
    now_ms = time.time() * 1000
    interval_total = int(raw.get("current_interval_total_count", 0))
    interval_used = int(raw.get("current_interval_usage_count", 0))
    weekly_total = int(raw.get("current_weekly_total_count", 0))
    weekly_used = int(raw.get("current_weekly_usage_count", 0))
    end_time = raw.get("end_time")
    reset_in_s = max(0, int((int(end_time) - now_ms) / 1000)) if end_time else 0
    return {
        "name": _short_name(str(raw.get("model_name", ""))),
        "label": str(raw.get("model_name", "")),
        "interval_total": interval_total,
        "interval_used": interval_used,
        "interval_pct": min(round(interval_used / interval_total * 100, 1), 100) if interval_total else 0,
        "interval_reset_in_s": reset_in_s,
        "weekly_total": weekly_total,
        "weekly_used": weekly_used,
        "weekly_pct": min(round(weekly_used / weekly_total * 100, 1), 100) if weekly_total else 0,
    }


def _set_cache(data: dict) -> dict:
    global _cache
    _cache = {"data": data, "fetched_at": time.time()}
    return data


async def fetch_usage() -> dict:
    """Cached MiniMax-Quota-Abfrage. Bei Fehler/no-key: {available: False, reason: ...}."""
    if _cache["data"] is not None and (time.time() - _cache["fetched_at"]) < _CACHE_TTL:
        return _cache["data"]

    key = get_provider_key(load_config(), "minimax")
    if not key:
        return _set_cache({"available": False, "reason": "no_api_key", "fetched_at": _iso_now()})

    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.minimax.io/v1/token_plan/remains",
                headers={"Authorization": f"Bearer {key}"},
            )
    except Exception as exc:
        logger.warning("minimax_usage HTTP fetch failed: %s", exc)
        return _set_cache({"available": False, "reason": "network_error", "fetched_at": _iso_now()})

    if resp.status_code == 401:
        return _set_cache({"available": False, "reason": "invalid_api_key", "fetched_at": _iso_now()})
    if resp.status_code >= 400:
        return _set_cache({"available": False, "reason": f"http_{resp.status_code}", "fetched_at": _iso_now()})

    try:
        raw = resp.json()
    except ValueError:
        return _set_cache({"available": False, "reason": "invalid_json", "fetched_at": _iso_now()})

    model_list = raw.get("model_remains") if isinstance(raw, dict) else []
    if not isinstance(model_list, list):
        model_list = []
    models = [_normalize_model(m) for m in model_list if isinstance(m, dict)]
    return _set_cache({"available": True, "fetched_at": _iso_now(), "models": models})
