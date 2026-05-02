"""Persistent Daily-Cap für TTS-Calls — deterministisch, kein LLM.

Speichert pro User einen Counter in JSON unter `<data_dir>/.tts_quota.json`.
Reset um Mitternacht UTC (vergleicht ISO-Datum). Atomarer Schreibvorgang
via temp-file + rename.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_DAILY_CAP = 200
_LOCK = threading.Lock()


def _path() -> Path:
    return settings.data_dir / ".tts_quota.json"


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load() -> dict:
    p = _path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def get_cap() -> int:
    """Daily-Cap aus ENV (TTS_DAILY_CAP) oder Default."""
    raw = os.environ.get("TTS_DAILY_CAP", "").strip()
    if raw and raw.isdigit():
        return max(0, int(raw))
    return DEFAULT_DAILY_CAP


def check_and_increment(username: str) -> tuple[bool, int, int]:
    """Idempotent: erhöht den Counter wenn unter Cap. Returnt (allowed, used, cap).

    Bei `allowed=False` wurde NICHT inkrementiert — Caller darf den Synthese-
    Subprocess nicht starten.
    """
    cap = get_cap()
    today = _today_utc()
    with _LOCK:
        data = _load()
        per_user = data.get(username, {})
        if per_user.get("date") != today:
            per_user = {"date": today, "count": 0}
        used = per_user["count"]
        if used >= cap:
            return False, used, cap
        per_user["count"] = used + 1
        data[username] = per_user
        _save(data)
        return True, used + 1, cap
