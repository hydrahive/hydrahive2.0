"""Client: Anstupsen vom eigenen Hub annehmen (docs/specs/federation-shared-tasks.md
§Anstupsen catalog_notify).

Prüfung wie bei ``catalog_fetch`` (catalog_origin): Absender ist der eigene,
aktive Hub (Signatur und Frische prüft die Route mit ``verify_incoming``),
``msg_id`` neu (Replay-Schutz im Speicher, gleiche Single-Worker-Annahme wie
catalog_origin). Jeder Fehler ergibt nach außen ``404``, der Grund geht nur ins
Audit.

Angenommene Anstupser lösen GEBÜNDELT ein Abholen aus: Läuft schon eines oder
ist eines angestoßen, kommt kein zweites dazu, sondern höchstens eines danach
(falls während des Laufs neu angestupst wurde). Die Route wartet nie darauf.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time

from hydrahive.db import federation_catalog_client as client_db
from hydrahive.federation import catalog_pull_client
from hydrahive.federation import peer_protocol as proto
from hydrahive.federation.catalog_origin import Unavailable

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_seen: dict[str, float] = {}      # msg_id → läuft ab (monotonic)
_state = {"running": False, "again": False}
_tasks: set[asyncio.Task] = set()


def _remember(msg_id: str) -> bool:
    now = time.monotonic()
    with _lock:
        for key in [k for k, until in _seen.items() if until <= now]:
            del _seen[key]
        if msg_id in _seen:
            return False
        _seen[msg_id] = now + proto.MAX_AGE_SECONDS + proto.MAX_SKEW_SECONDS
        return True


def check(peer: dict, payload: dict) -> None:
    """Schritte nach der Signaturprüfung. Wirft Unavailable (→ 404)."""
    cfg = client_db.load_config()
    if not peer.get("is_hub") or not cfg.hub or cfg.hub.get("id") != peer.get("id"):
        raise Unavailable("peer_not_hub")
    rev = payload.get("rev")
    if not isinstance(rev, int) or isinstance(rev, bool) or rev < 0:
        raise Unavailable("payload_invalid")
    if not _remember(payload["msg_id"]):
        raise Unavailable("peer_replay")


async def _run() -> None:
    try:
        while True:
            with _lock:
                _state["again"] = False
            await catalog_pull_client.pull(reason="notify")    # wirft nie
            with _lock:
                if not _state["again"]:
                    _state["running"] = False
                    return
    except BaseException:
        with _lock:
            _state["running"] = False
        raise


def trigger() -> bool:
    """Abholen anstoßen, ohne zu warten. Rückgabe: ein neuer Lauf wurde gestartet."""
    with _lock:
        if _state["running"]:
            _state["again"] = True
            return False
        _state["running"] = True
    task = asyncio.get_running_loop().create_task(_run(), name="federation-catalog-notify-pull")
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return True


def _reset_for_tests() -> None:
    with _lock:
        _seen.clear()
        _state.update(running=False, again=False)
