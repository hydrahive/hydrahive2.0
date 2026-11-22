"""Serverseitiger Entsperr-Zustand des Vaults (Ziel vault-agenten §1.3, Etappe 1a).

Der Vault-Token liegt nur im Browser. Damit Agenten-Werkzeuge wissen, ob der Vault ihres Besitzers offen ist, hält
der Kern je Nutzer eine Zeile in ``vault_unlocks``: gesetzt beim Entsperren, verlängert bei jeder erfolgreichen
Vault-Anfrage (Oberfläche und Werkzeug), gelöscht beim Sperren, PIN-Wechsel und Reset. Dieselbe Uhr wie der Token
(``tokens.IDLE_SECONDS``, ``tokens.MAX_SECONDS``). Prüfen und Verlängern ist EIN UPDATE – mehrere Worker sehen
denselben Stand, ein Neustart ändert nichts.
"""
from __future__ import annotations

import time

from hydrahive.db.connection import db
from hydrahive.vault import pins, tokens


def open_(user_id: str, *, generation: int) -> None:
    """Entsperrt (PIN geprüft). Ersetzt einen älteren Zustand."""
    now = time.time()
    with db() as c:
        c.execute(
            """INSERT INTO vault_unlocks (user_id, unlocked_at, last_used_at, generation) VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET unlocked_at = excluded.unlocked_at,
                   last_used_at = excluded.last_used_at, generation = excluded.generation""",
            (user_id, now, now, generation),
        )


def use(user_id: str) -> bool:
    """Offen? Dann gleich verlängern (gleitende Sperre). Sonst False – auch ohne PIN oder bei alter generation."""
    if not pins.is_set(user_id):
        return False
    now = time.time()
    with db() as c:
        cur = c.execute(
            """UPDATE vault_unlocks SET last_used_at = ?
               WHERE user_id = ? AND generation = ? AND ? - last_used_at <= ? AND ? - unlocked_at <= ?""",
            (now, user_id, pins.generation(user_id), now, tokens.IDLE_SECONDS, now, tokens.MAX_SECONDS),
        )
        return cur.rowcount == 1


def close(user_id: str) -> None:
    """Sofort gesperrt (Sperren, PIN-Wechsel, Reset)."""
    with db() as c:
        c.execute("DELETE FROM vault_unlocks WHERE user_id = ?", (user_id,))
