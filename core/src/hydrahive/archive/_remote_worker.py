"""Hintergrund-Thread der Kopier-Reihe zum NAS (Spec archiv-system.md, Etappe 3). Ausgelagert aus remote_sync.py."""
from __future__ import annotations

import logging
import threading

from hydrahive.archive import remote_config, remote_sync

logger = logging.getLogger(__name__)

_wake = threading.Event()
_thread: threading.Thread | None = None


def _worker() -> None:
    while True:
        try:
            remote_sync.process_queue()
        except Exception:  # noqa: BLE001 – der Thread darf nie still sterben
            logger.exception("Kopier-Reihe zum NAS: unerwarteter Fehler")
        nxt = remote_sync.summary()["next_try_in_s"]
        _wake.wait(timeout=min(nxt if nxt else 3600, 3600))
        _wake.clear()


def start() -> None:
    global _thread
    with remote_sync._lock:
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_worker, name="archive-remote", daemon=True)
            _thread.start()
    _wake.set()


def on_start() -> None:
    """Beim Dienststart: Reihe weiter, Abgleich (holt alles nach, was fehlt)."""
    if not remote_config.is_active():
        return
    try:
        remote_sync.sync()
    except Exception:  # noqa: BLE001 – NAS beim Start weg: die Reihe versucht es später
        logger.info("Abgleich mit dem NAS beim Start nicht möglich, später neuer Versuch")
    start()
