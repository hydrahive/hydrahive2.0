"""Speicher der Agenten-Templates: `$HH_CONFIG_DIR/agent_templates.json`.

Schreiben unter Prozess-Sperre + Datei-Sperre (fcntl), atomar über Temp-Datei. Lesen mit mtime-Cache.
Format: {"version": 1, "templates": {id: {...}}, "history": {id: [ältere Fassungen]}}.
"""
from __future__ import annotations

import fcntl
import json
import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

FORMAT_VERSION = 1
HISTORY_KEEP = 20

_lock = threading.RLock()
_cache: tuple[float, dict] | None = None


def _path() -> Path:
    return settings.config_dir / "agent_templates.json"


def reset_cache() -> None:
    global _cache
    _cache = None


def _empty() -> dict:
    return {"version": FORMAT_VERSION, "templates": {}, "history": {}}


def _read() -> dict:
    path = _path()
    if not path.exists():
        return _empty()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("agent_templates.json nicht lesbar (%s) — leere Templates", exc)
        return _empty()
    data.setdefault("templates", {})
    data.setdefault("history", {})
    return data


def load() -> dict:
    """Aktueller Stand (nicht verändern – Kopie über `mutate`)."""
    global _cache
    path = _path()
    mtime = path.stat().st_mtime if path.exists() else -1.0
    with _lock:
        if _cache and _cache[0] == mtime:
            return _cache[1]
        data = _read()
        _cache = (mtime, data)
        return data


def _write(data: dict) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


@contextmanager
def mutate() -> Iterator[dict]:
    """Lesen–Ändern–Schreiben unter Sperre. Der übergebene dict wird nach dem Block gespeichert."""
    global _cache
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock, open(path.with_suffix(".lock"), "a+") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            data = _read()
            yield data
            _write(data)
            _cache = None
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def push_history(data: dict, template_id: str, old: dict) -> None:
    hist = data["history"].setdefault(template_id, [])
    hist.append(old)
    del hist[:-HISTORY_KEEP]
