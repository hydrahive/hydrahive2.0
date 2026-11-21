"""Client: Katalog-Sync automatisch auslösen (docs/specs/federation-catalog.md §Ablauf 2).

Zwei Hintergrund-Loops mit gemeinsamem Stop-Event, gestartet in ``api/lifespan.py``:

- **Timer** (``run_timer``): erster Lauf ``FIRST_DELAY`` (60 s) nach dem Start,
  danach ``interval_seconds`` — bei jedem Durchlauf neu aus den Einstellungen,
  damit Änderungen ohne Neustart wirken. Jeder Lauf schickt das Delta (oder ein
  leeres Lebenszeichen); ist der Abgleich fällig (``full_due``), auch die
  Versionsliste.
- **Event-Push** (``run_events``): ``ctx.catalog_changed`` merkt im Speicher vor
  (``catalog_changes``, aus beliebigen Threads). Der Loop sieht das spätestens
  nach ``POLL`` (1 s, reiner Speicherzugriff), wartet ``BUNDLE`` (10 s) Bündelung
  ab und schickt dann EINEN Lauf. Überlauf → voller Delta-Lauf. Scheitert der
  Push, gibt es keine Wiederholung: der Cursor bleibt stehen, der Timer holt nach.

Beide nutzen ``catalog_sync.sync`` und damit dieselbe Sperre. Ist der Sync aus,
kein aktiver Hub gesetzt oder kein Nutzer gewählt, entsteht kein Netzverkehr:
``sync`` liefert dann ``inactive``, und ``catalog_changes`` merkt gar nicht erst vor.
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.db import federation_catalog_client as client_db
from hydrahive.federation import catalog_changes, catalog_sync

logger = logging.getLogger(__name__)

FIRST_DELAY = 60.0     # Sekunden bis zum ersten Timer-Lauf
FALLBACK_INTERVAL = 300
MIN_INTERVAL = 60      # Spec: einstellbar 60–3600 s
MAX_INTERVAL = 3600
BUNDLE = 10.0          # Event-Push: Bündelung ab der ersten Vormerkung
POLL = 1.0             # wie oft der Event-Loop nach Vormerkungen schaut


async def _wait(stop: asyncio.Event, seconds: float) -> bool:
    """Wartet ``seconds`` oder bis ``stop`` gesetzt ist. True = Stop."""
    if stop.is_set():
        return True
    try:
        await asyncio.wait_for(stop.wait(), timeout=max(0.0, seconds))
    except asyncio.TimeoutError:
        return False
    return True


def _interval() -> int:
    try:
        value = int(client_db.load_config().interval_seconds)
    except Exception as e:
        logger.warning("Katalog-Sync: Intervall nicht lesbar, nehme %s s: %s", FALLBACK_INTERVAL, e)
        return FALLBACK_INTERVAL
    return min(MAX_INTERVAL, max(MIN_INTERVAL, value))


async def timer_tick(runs: int) -> str:
    """Ein Timer-Lauf. ``runs`` zählt die Timer-Läufe seit dem Start (ab 1)."""
    try:
        cfg = await asyncio.to_thread(client_db.load_config)
    except Exception as e:
        logger.warning("Katalog-Sync: Einstellungen nicht lesbar: %s", e)
        return "sync_failed"
    if not cfg.active:
        return "inactive"
    full = catalog_sync.full_due(cfg.last_full_at, runs)
    return await catalog_sync.sync(full=full, reason="timer")


async def event_tick() -> str | None:
    """Vorgemerktes abholen und schicken. None = nichts vorgemerkt."""
    entries, overflow = catalog_changes.drain()
    if overflow:
        return await catalog_sync.sync(reason="overflow")
    if not entries:
        return None
    pairs = {(username, kind) for kind, username, _item in entries}
    return await catalog_sync.sync(pairs=pairs, entries=entries, heartbeat=False, reason="event")


async def run_timer(stop: asyncio.Event) -> None:
    if await _wait(stop, FIRST_DELAY):
        return
    runs = 0
    while not stop.is_set():
        runs += 1
        try:
            await timer_tick(runs)
        except Exception as e:  # sync wirft nie; reine Absicherung des Loops
            logger.warning("Katalog-Sync: Timer-Lauf fehlgeschlagen: %s", e, exc_info=True)
        if await _wait(stop, await asyncio.to_thread(_interval)):
            return


async def run_events(stop: asyncio.Event) -> None:
    while not stop.is_set():
        if await _wait(stop, POLL):
            return
        if not catalog_changes.is_dirty():
            continue
        if await _wait(stop, BUNDLE):   # bündeln: weitere Änderungen dürfen dazukommen
            return
        try:
            await event_tick()
        except Exception as e:
            logger.warning("Katalog-Sync: Event-Push fehlgeschlagen: %s", e, exc_info=True)


def start(stop: asyncio.Event) -> list[asyncio.Task]:
    """Startet Timer- und Event-Loop. Beide enden, sobald ``stop`` gesetzt ist."""
    return [
        asyncio.create_task(run_timer(stop), name="federation-catalog-timer"),
        asyncio.create_task(run_events(stop), name="federation-catalog-events"),
    ]
