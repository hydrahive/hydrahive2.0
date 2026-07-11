"""OpenAI Codex Plan-Usage — `GET /backend-api/wham/usage`.

Nutzt die vorhandene Codex-OAuth (ChatGPT Plus/Pro). Liefert primary (5h) +
secondary (7d) Fenster mit used_percent + reset — strukturgleich zu Anthropic.
Das Frontend zeigt daraus 5h/7d-Balken mit Reset-Timer in der Cockpit-Box.

30s In-Module-Cache verhindert Endpoint-Spam beim Cockpit-Polling.
Bei fehlendem OAuth / Fehler: {available: False, reason: ...} — UI blendet aus.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}
_CACHE_TTL = 30.0

_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _set_cache(data: dict) -> dict:
    global _cache
    _cache = {"data": data, "fetched_at": time.time()}
    return data


def _normalize_window(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    try:
        used_pct = float(raw.get("used_percent") or 0)
        reset_in_s = int(raw.get("reset_after_seconds") or 0)
        window_s = int(raw.get("limit_window_seconds") or 0)
    except (TypeError, ValueError):
        return None
    return {
        "used_pct": min(round(used_pct, 1), 100.0),
        "reset_in_s": max(0, reset_in_s),
        "window_s": window_s,
    }


async def fetch_usage() -> dict:
    """Cached Codex-Plan-Usage-Abfrage.

    Erfolg: {available: True, plan_type, primary, secondary, credits, fetched_at}
    Fehler/no-oauth: {available: False, reason: ...}
    """
    if _cache["data"] is not None and (time.time() - _cache["fetched_at"]) < _CACHE_TTL:
        return _cache["data"]

    try:
        from hydrahive.oauth.openai_codex import resolve_openai_codex_token
        tok = await resolve_openai_codex_token()
    except Exception as exc:
        logger.debug("codex_usage token resolve failed: %s", exc)
        return _set_cache({"available": False, "reason": "no_oauth", "fetched_at": _iso_now()})

    access = tok.get("access", "")
    account_id = tok.get("account_id", "")
    if not access:
        return _set_cache({"available": False, "reason": "no_oauth", "fetched_at": _iso_now()})

    import httpx

    headers = {"Authorization": f"Bearer {access}"}
    if account_id:
        headers["ChatGPT-Account-ID"] = account_id

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_USAGE_URL, headers=headers)
    except Exception as exc:
        logger.warning("codex_usage HTTP fetch failed: %s", exc)
        return _set_cache({"available": False, "reason": "network_error", "fetched_at": _iso_now()})

    if resp.status_code in (401, 403):
        return _set_cache({"available": False, "reason": "unauthorized", "fetched_at": _iso_now()})
    if resp.status_code >= 400:
        return _set_cache({"available": False, "reason": f"http_{resp.status_code}", "fetched_at": _iso_now()})

    try:
        raw = resp.json()
    except ValueError:
        return _set_cache({"available": False, "reason": "invalid_json", "fetched_at": _iso_now()})

    if not isinstance(raw, dict):
        return _set_cache({"available": False, "reason": "invalid_json", "fetched_at": _iso_now()})

    rate = raw.get("rate_limit") or {}
    primary = _normalize_window(rate.get("primary_window"))
    secondary = _normalize_window(rate.get("secondary_window"))
    if primary is None and secondary is None:
        return _set_cache({"available": False, "reason": "no_data", "fetched_at": _iso_now()})

    credits_raw = raw.get("credits") or {}
    credits: dict[str, Any] = {}
    if isinstance(credits_raw, dict):
        credits = {
            "has_credits": bool(credits_raw.get("has_credits")),
            "unlimited": bool(credits_raw.get("unlimited")),
        }
        balance = credits_raw.get("balance")
        if balance is not None:
            try:
                credits["balance"] = float(balance)
            except (TypeError, ValueError):
                pass

    return _set_cache({
        "available": True,
        "fetched_at": _iso_now(),
        "plan_type": str(raw.get("plan_type") or ""),
        "primary": primary,
        "secondary": secondary,
        "credits": credits,
    })
