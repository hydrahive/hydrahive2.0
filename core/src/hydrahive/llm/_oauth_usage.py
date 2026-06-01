"""OAuth Usage Cache — extrahiert + speichert Rate-Limit-Header von Anthropic.

Nach jedem Anthropic-API-Call (OAuth oder plain Bearer) extrahieren wir die
anthropic-ratelimit-unified-* Header und persistieren sie in oauth_usage.json.

Frontend/API kann dann darauf zugreifen ohne extra API-Call.

Portiert aus HH1 orchestrator_llm.py Zeile 140-224.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_CACHE_FILE = settings.data_dir / "oauth_usage.json"

_oauth_rate_limits: dict[str, Any] = {}


def _load_cache() -> dict:
    """Beim Start gespeicherte OAuth-Daten von Disk laden."""
    try:
        if _CACHE_FILE.exists():
            return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("OAuth-Usage-Cache laden fehlgeschlagen: %s", e)
    return {}


def _save_cache(data: dict) -> None:
    """OAuth-Daten auf Disk persistieren (fire-and-forget)."""
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("OAuth-Usage-Cache schreiben fehlgeschlagen: %s", e)


def extract_rate_limit_headers(headers: dict | Any) -> None:
    """Anthropic Rate-Limit Headers parsen und in globalem State speichern.

    Headers (anthropic-ratelimit-unified-*):
    - 5h-utilization, 5h-reset, 5h-surpassed-threshold
    - 7d-utilization, 7d-reset, 7d-surpassed-threshold
    - overage-utilization, overage-reset, overage-status
    - status, representative-claim, fallback
    """
    if not headers:
        return

    # headers kann dict oder httpx.Headers-Objekt sein
    if hasattr(headers, "get"):
        get_header = headers.get
    else:
        return

    prefix = "anthropic-ratelimit-unified-"
    data: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}

    for key in ("status", "representative-claim", "fallback", "reset"):
        val = get_header(f"{prefix}{key}")
        if val:
            data[key.replace("-", "_")] = val

    for window in ("5h", "7d"):
        util = get_header(f"{prefix}{window}-utilization")
        reset = get_header(f"{prefix}{window}-reset")
        threshold = get_header(f"{prefix}{window}-surpassed-threshold")
        if util is not None:
            try:
                data[f"{window}_utilization"] = float(util)
            except ValueError:
                pass
        if reset:
            data[f"{window}_reset"] = reset
        if threshold:
            data[f"{window}_surpassed_threshold"] = threshold

    # Overage / Extra Usage
    for key in (
        "overage-status",
        "overage-reset",
        "overage-utilization",
        "overage-disabled-reason",
        "overage-surpassed-threshold",
    ):
        val = get_header(f"{prefix}{key}")
        if val:
            k = key.replace("-", "_")
            if "utilization" in key:
                try:
                    data[k] = float(val)
                except ValueError:
                    data[k] = val
            else:
                data[k] = val

    if len(data) > 1:  # mehr als nur updated_at
        global _oauth_rate_limits
        _oauth_rate_limits = data
        _save_cache(data)


def get_oauth_rate_limits() -> dict:
    """Aktuelle OAuth Rate-Limit-Daten abrufen (für API-Endpoint)."""
    return dict(_oauth_rate_limits)


# Beim Import: Cache laden
_oauth_rate_limits = _load_cache()
