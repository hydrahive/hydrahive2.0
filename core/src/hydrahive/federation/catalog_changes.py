"""Vormerkliste für `ctx.catalog_changed(...)` (docs/specs/federation-catalog.md,
docs/specs/federation-shared-tasks.md §Änderungsnummer).

Etappe 2: Module melden nach jedem Schreiben `(kind, username, item_id)`. Hier
wird nur vorgemerkt; der Event-Push (10 s gebündelt) kommt in Etappe 3 und holt
die Einträge mit `drain()` ab.

`mark_changed` liegt im Schreibpfad der Module und muss sofort zurückkehren. Es
liest deshalb keine Datenbank, sondern prüft einen Schalter im Speicher
(`_Gate`). Den setzt `refresh_gate()` neu: beim Start (lifespan) und nach jeder
Route, die Hub, Partnerstatus oder Katalog-Einstellungen ändert.

Zwei GETRENNTE Vormerklisten unter derselben Sperre:
- `_pending`/`drain()`: Client-Push (Etappe 3, unverändert) — aktiv, wenn
  diese Instanz einen eigenen Hub hat, Sync läuft und der Nutzer ausgewählt
  ist.
- `_pending_hub`/`drain_hub()`: eigene Hub-Einträge (Auftrag B3) — aktiv,
  wenn diese Instanz SELBST Hub ist (mind. ein Partner mit
  `catalog_accept=1`) UND ihr eigenes `shared` an ist. Eine Instanz ohne
  eigenen Hub-Partner (Client) merkt hier NIE etwas vor, damit kein
  Client-Push ausgelöst wird — die beiden Listen sind komplett unabhängig.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from hydrahive.modules.context import CATALOG_KINDS

logger = logging.getLogger(__name__)

KINDS = frozenset(CATALOG_KINDS)  # eine Quelle der Wahrheit: modules/context.py
MAX_PENDING = 10_000  # darüber: nicht mehr einzeln merken, Timer-Lauf holt alles


@dataclass(frozen=True)
class _Gate:
    active: bool = False
    users: frozenset[str] = frozenset()
    hub_active: bool = False
    hub_users: frozenset[str] = frozenset()


_lock = threading.Lock()
_gate: _Gate = _Gate()          # Standard: aus, bis refresh_gate() gelaufen ist
_pending: set[tuple[str, str, str]] = set()
_pending_hub: set[tuple[str, str, str]] = set()
_overflow = False
_overflow_hub = False


def mark_changed(kind: str, username: str, item_id: str) -> None:
    """Merkt eine Änderung vor — Client-Push UND eigene Hub-Verteilung,
    unabhängig voneinander. Kehrt sofort zurück, wirft nie, keine I/O."""
    global _overflow, _overflow_hub
    try:
        gate = _gate
        if kind not in KINDS or not isinstance(username, str) or not isinstance(item_id, str) or not item_id:
            return
        want_client = gate.active and username in gate.users
        want_hub = gate.hub_active and username in gate.hub_users
        if not want_client and not want_hub:
            return
        with _lock:
            # zweite Prüfung unter der Sperre: refresh_gate kann dazwischen
            # abgeschaltet und geleert haben
            if _gate.active and username in _gate.users:
                if len(_pending) >= MAX_PENDING:
                    _overflow = True
                else:
                    _pending.add((kind, username, item_id))
            if _gate.hub_active and username in _gate.hub_users:
                if len(_pending_hub) >= MAX_PENDING:
                    _overflow_hub = True
                else:
                    _pending_hub.add((kind, username, item_id))
    except Exception as e:  # pragma: no cover - reine Absicherung
        logger.debug("Katalog-Vormerkung verworfen: %s", e)


def drain() -> tuple[list[tuple[str, str, str]], bool]:
    """Holt alle vorgemerkten Einträge für den CLIENT-Push ab und leert die
    Liste (Etappe 3). Unverändert — kennt die Hub-Liste nicht.

    Rückgabe: (Einträge sortiert, overflow). overflow=True heißt, es gingen
    Vormerkungen verloren; dann ist ein voller Timer-Lauf nötig.
    """
    global _overflow
    with _lock:
        items = sorted(_pending)
        over = _overflow
        _pending.clear()
        _overflow = False
    return items, over


def drain_hub() -> tuple[list[tuple[str, str, str]], bool]:
    """Holt alle vorgemerkten eigenen Hub-Einträge ab und leert die Liste
    (Auftrag B3, `hub_distribute_step()` in catalog_hub_own.py). Unabhängig
    von `drain()` — löst nie einen Client-Push aus."""
    global _overflow_hub
    with _lock:
        items = sorted(_pending_hub)
        over = _overflow_hub
        _pending_hub.clear()
        _overflow_hub = False
    return items, over


def pending_count() -> int:
    with _lock:
        return len(_pending)


def pending_hub_count() -> int:
    with _lock:
        return len(_pending_hub)


def is_dirty() -> bool:
    with _lock:
        return bool(_pending) or _overflow


def is_hub_dirty() -> bool:
    with _lock:
        return bool(_pending_hub) or _overflow_hub


def gate_active() -> bool:
    return _gate.active


def hub_gate_active() -> bool:
    return _gate.hub_active


def refresh_gate() -> bool:
    """Liest Einstellungen + Hub aus der DB und setzt BEIDE Schalter neu
    (Client-Push und eigene Hub-Verteilung).

    Wird aus Routen und beim Start aufgerufen, nie aus `mark_changed`. Fehler
    werden geloggt und schalten beide Vormerkungen ab (lieber nichts merken
    als falsch). Wird ein Schalter inaktiv, wird seine Liste geleert; Nutzer,
    die nicht mehr ausgewählt sind, fliegen heraus. Rückgabe: Client-Schalter
    (unverändertes Verhalten für bestehende Aufrufer).
    """
    global _gate, _overflow, _overflow_hub
    try:
        from hydrahive.db import federation_catalog as catalog_db

        enabled, hub_status, selected = catalog_db.gate_inputs()
        users = frozenset(selected)
        active = enabled and hub_status == "active" and bool(users)

        is_hub, hub_shared, hub_selected = catalog_db.hub_gate_inputs()
        hub_users = frozenset(hub_selected)
        hub_active = is_hub and hub_shared and bool(hub_users)

        new = _Gate(
            active=active, users=users if active else frozenset(),
            hub_active=hub_active, hub_users=hub_users if hub_active else frozenset(),
        )
    except Exception as e:
        logger.warning("Katalog-Schalter konnte nicht gelesen werden, Vormerken aus: %s", e)
        new = _Gate()
    with _lock:
        _gate = new
        if not new.active:
            _pending.clear()
            _overflow = False
        else:
            _pending.difference_update({p for p in _pending if p[1] not in new.users})
        if not new.hub_active:
            _pending_hub.clear()
            _overflow_hub = False
        else:
            _pending_hub.difference_update({p for p in _pending_hub if p[1] not in new.hub_users})
    return new.active


def safe_refresh_gate() -> None:
    """Für Routen: aktualisiert den Schalter, ohne die Antwort zu gefährden."""
    try:
        refresh_gate()
    except Exception as e:  # pragma: no cover - refresh_gate fängt selbst
        logger.warning("Katalog-Schalter: Aktualisierung fehlgeschlagen: %s", e)


def _reset_for_tests() -> None:
    global _gate, _overflow, _overflow_hub
    with _lock:
        _gate = _Gate()
        _pending.clear()
        _pending_hub.clear()
        _overflow = False
        _overflow_hub = False
