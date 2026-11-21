"""Vormerkliste für `ctx.catalog_changed(...)` (docs/specs/federation-catalog.md).

Etappe 2: Module melden nach jedem Schreiben `(kind, username, item_id)`. Hier
wird nur vorgemerkt; der Event-Push (10 s gebündelt) kommt in Etappe 3 und holt
die Einträge mit `drain()` ab.

`mark_changed` liegt im Schreibpfad der Module und muss sofort zurückkehren. Es
liest deshalb keine Datenbank, sondern prüft einen Schalter im Speicher
(`_Gate`). Den setzt `refresh_gate()` neu: beim Start (lifespan) und nach jeder
Route, die Hub, Partnerstatus oder Katalog-Einstellungen ändert. Ist der Sync
aus, kein aktiver Hub gesetzt oder der Nutzer nicht ausgewählt, passiert nichts.
Verpasst die Vormerkung etwas, holt es der Timer-Lauf (Etappe 3) über den
Cursor nach.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)

KINDS = frozenset({"task", "idea"})
MAX_PENDING = 10_000  # darüber: nicht mehr einzeln merken, Timer-Lauf holt alles


@dataclass(frozen=True)
class _Gate:
    active: bool = False
    users: frozenset[str] = frozenset()


_lock = threading.Lock()
_gate: _Gate = _Gate()          # Standard: aus, bis refresh_gate() gelaufen ist
_pending: set[tuple[str, str, str]] = set()
_overflow = False


def mark_changed(kind: str, username: str, item_id: str) -> None:
    """Merkt eine Änderung vor. Kehrt sofort zurück, wirft nie, keine I/O."""
    global _overflow
    try:
        gate = _gate
        if not gate.active or kind not in KINDS:
            return
        if not isinstance(username, str) or username not in gate.users:
            return
        if not isinstance(item_id, str) or not item_id:
            return
        with _lock:
            if len(_pending) >= MAX_PENDING:
                _overflow = True
                return
            _pending.add((kind, username, item_id))
    except Exception as e:  # pragma: no cover - reine Absicherung
        logger.debug("Katalog-Vormerkung verworfen: %s", e)


def drain() -> tuple[list[tuple[str, str, str]], bool]:
    """Holt alle vorgemerkten Einträge ab und leert die Liste (für Etappe 3).

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


def pending_count() -> int:
    with _lock:
        return len(_pending)


def is_dirty() -> bool:
    with _lock:
        return bool(_pending) or _overflow


def gate_active() -> bool:
    return _gate.active


def refresh_gate() -> bool:
    """Liest Einstellungen + Hub aus der DB und setzt den Schalter neu.

    Wird aus Routen und beim Start aufgerufen, nie aus `mark_changed`. Fehler
    werden geloggt und schalten das Vormerken ab (lieber nichts merken als
    falsch). Wird der Schalter inaktiv, wird die Vormerkliste geleert;
    Nutzer, die nicht mehr ausgewählt sind, fliegen heraus.
    """
    global _gate, _overflow
    try:
        from hydrahive.db import federation_catalog as catalog_db

        enabled, hub_status, selected = catalog_db.gate_inputs()
        users = frozenset(selected)
        active = enabled and hub_status == "active" and bool(users)
        new = _Gate(active=active, users=users if active else frozenset())
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
    return new.active


def safe_refresh_gate() -> None:
    """Für Routen: aktualisiert den Schalter, ohne die Antwort zu gefährden."""
    try:
        refresh_gate()
    except Exception as e:  # pragma: no cover - refresh_gate fängt selbst
        logger.warning("Katalog-Schalter: Aktualisierung fehlgeschlagen: %s", e)


def _reset_for_tests() -> None:
    global _gate, _overflow
    with _lock:
        _gate = _Gate()
        _pending.clear()
        _overflow = False
