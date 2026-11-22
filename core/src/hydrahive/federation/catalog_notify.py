"""Hub: Clients anstupsen (docs/specs/federation-shared-tasks.md §Anstupsen catalog_notify).

Ändert sich am Hub etwas, das Clients sehen (Upsert oder Löschung aus einem
Push, eigene Änderung des Hubs), ruft der Auslöser ``mark()`` (beim Push mit
``exclude`` = Absender: seine eigenen Einträge bekommt er nie). Der Event-Loop
ruft ``flush()``: Für jeden berechtigten Empfänger (Bedingung 3: catalog_accept,
active, meldet shared) geht höchstens EIN ``catalog_notify`` je ``WINDOW_S``
raus, ohne Daten und ohne Wiederholung. Wer im Fenster schon angestupst wurde,
bleibt vorgemerkt und wird nach Ablauf des Fensters bedient. Geht ein
Anstupser verloren, holt der nächste Timer-Lauf des Clients die Änderung.

``flush`` wirft nie und wartet höchstens ``SEND_TIMEOUT`` je Client; alle
Clients werden gleichzeitig angestupst, ein langsamer hält keinen anderen auf.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time

import httpx

from hydrahive.db import federation_catalog as catalog_db
from hydrahive.db.connection import db
from hydrahive.federation import peer_protocol as proto

logger = logging.getLogger(__name__)

NOTIFY_PATH = "/api/peering/catalog/notify"
WINDOW_S = 10.0
SEND_TIMEOUT = 5.0

_lock = threading.Lock()
_marks: list[str | None] = []         # je Änderung: ausgenommener Absender (oder None)
_waiting: set[str] = set()            # Empfänger, deren Anstupser noch aussteht
_last_sent: dict[str, float] = {}     # peer_id → monotonic des letzten Anstupsers
_MAX_MARKS = 1000


def mark(exclude: str | None = None) -> None:
    """„Am Hub hat sich etwas geändert.“ Kehrt sofort zurück, wirft nie."""
    with _lock:
        if len(_marks) < _MAX_MARKS:
            _marks.append(exclude)
        elif None not in _marks:
            _marks.append(None)           # zu viele: alle anstupsen


def pending() -> bool:
    with _lock:
        return bool(_marks or _waiting)


def recipients(exclude: str | None = None) -> list[dict]:
    """Berechtigte Empfänger (Bedingung 3). ``exclude``: Absender des auslösenden Pushs."""
    if not catalog_db.get_settings().get("shared"):        # Bedingung 1: Hub teilt
        return []
    with db() as conn:
        rows = conn.execute(
            "SELECT p.* FROM federation_peers p JOIN federation_catalog_sources s ON s.peer_id = p.id "
            "WHERE p.catalog_accept = 1 AND p.status = 'active' AND s.shared = 1 ORDER BY p.name",
        ).fetchall()
    return [dict(r) for r in rows if r["id"] != exclude]


async def _send(peer: dict, payload: dict) -> bool:
    try:
        async with httpx.AsyncClient(timeout=SEND_TIMEOUT, verify=False) as client:  # noqa: S501 - Ed25519
            r = await client.post(peer["url"] + NOTIFY_PATH, json=payload, headers=proto.signed_headers(payload))
        return r.status_code < 400
    except Exception as e:  # Anstupsen ist nur ein Hinweis, nie ein Fehler des Hubs
        logger.info("Katalog: Anstupsen von %s fehlgeschlagen: %s", peer.get("name"), e)
        return False


def current_rev() -> int:
    with db() as conn:
        row = conn.execute("SELECT rev FROM federation_catalog_counter WHERE id = 1").fetchone()
    return int(row["rev"]) if row else 0


async def flush(now: float | None = None) -> int:
    """Vorgemerktes Anstupsen ausführen. Rückgabe: Anzahl gesendeter Anstupser. Wirft nie."""
    if not pending():
        return 0
    try:
        peers = {p["id"]: p for p in await asyncio.to_thread(recipients)}
        rev = await asyncio.to_thread(current_rev)
    except Exception as e:
        logger.warning("Katalog: Empfänger fürs Anstupsen nicht lesbar: %s", e)
        return 0
    now = time.monotonic() if now is None else now
    with _lock:
        for exclude in _marks:
            _waiting.update(pid for pid in peers if pid != exclude)
        _marks.clear()
        _waiting.intersection_update(peers)   # nicht mehr berechtigt: vergessen
        due = [peers[pid] for pid in sorted(_waiting)
               if now - _last_sent.get(pid, float("-inf")) >= WINDOW_S]
        for p in due:
            _last_sent[p["id"]] = now
            _waiting.discard(p["id"])
    if not due:
        return 0
    results = await asyncio.gather(*(_send(p, proto.new_catalog_notify(rev)) for p in due),
                                   return_exceptions=True)   # ein Fehler darf nichts blockieren
    return sum(1 for r in results if r is True)


def _reset_for_tests() -> None:
    with _lock:
        _marks.clear()
        _waiting.clear()
        _last_sent.clear()
