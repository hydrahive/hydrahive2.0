"""Archiv-Umzug im Hintergrund mit Fortschritt für das Admin-Fenster (Spec archiv-system.md, Etappe 1b).

Ein Umzug zur Zeit, in einem eigenen Thread (die Ereignisschleife bleibt frei). Der Fortschritt steht im Speicher;
nach einem Neustart bringt move.recover() den Zustand wieder in Ordnung, „last“ ist dann leer.
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from hydrahive.archive import move

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_thread: threading.Thread | None = None
_running: dict | None = None
_last: dict | None = None


def snapshot() -> dict:
    with _lock:
        return {"running": dict(_running) if _running else None, "last": dict(_last) if _last else None}


def _progress(state: dict) -> None:
    global _running
    with _lock:
        _running = {**state, "updated": time.time()}


def _work(target: Path) -> None:
    global _running, _last
    try:
        result = move.run_move(target, on_progress=_progress)
    except Exception as e:  # noqa: BLE001 – Hintergrund-Thread darf nie still sterben
        logger.exception("Archiv-Umzug unerwartet abgebrochen")
        move.recover()
        result = {"state": "failed", "error": "unexpected", "detail": str(e)}
    with _lock:
        _running, _last = None, {**result, "finished": time.time()}


def start(target: Path) -> bool:
    """False, wenn schon ein Umzug läuft."""
    global _thread, _running
    with _lock:
        if _thread is not None and _thread.is_alive():
            return False
        _running = {"state": "starting", "target": str(target), "copied_bytes": 0, "total_bytes": 0}
        _thread = threading.Thread(target=_work, args=(Path(target),), name="archive-move", daemon=True)
        _thread.start()
    return True


def wait(timeout: float) -> None:
    t = _thread
    if t is not None:
        t.join(timeout)
