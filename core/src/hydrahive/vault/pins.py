"""Vault-PIN je Nutzer: setzen, prüfen, zurücksetzen (docs/specs/vault.md §4.2, §4.4).

Nur bcrypt-Hash wird gespeichert. Jede Änderung und jeder Reset erhöht ``generation``; Vault-Tokens mit einer
älteren generation gelten danach nicht mehr (tokens.py).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import bcrypt

from hydrahive.db.connection import db

_FORMAT = re.compile(r"[0-9]{6,12}")


class PinFormatError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row(user_id: str):
    with db() as c:
        return c.execute("SELECT pin_hash, generation FROM vault_pins WHERE user_id = ?", (user_id,)).fetchone()


def is_set(user_id: str) -> bool:
    row = _row(user_id)
    return bool(row and row["pin_hash"])


def generation(user_id: str) -> int:
    row = _row(user_id)
    return int(row["generation"]) if row else 0


def verify(user_id: str, pin: str) -> bool:
    row = _row(user_id)
    if not (row and row["pin_hash"] and isinstance(pin, str) and _FORMAT.fullmatch(pin)):
        return False
    return bcrypt.checkpw(pin.encode(), row["pin_hash"].encode())


def set_pin(user_id: str, pin: str) -> int:
    """PIN setzen oder ändern. Gibt die neue generation zurück."""
    if not isinstance(pin, str) or not _FORMAT.fullmatch(pin):
        raise PinFormatError("Die PIN muss aus 6 bis 12 Ziffern bestehen.")
    hashed = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
    return _write(user_id, hashed)


def reset(user_id: str) -> int:
    """PIN entfernen (vergessen/Admin). Daten bleiben. Gibt die neue generation zurück."""
    return _write(user_id, None)


def bump(user_id: str) -> int:
    """Sofort sperren: generation +1, PIN bleibt. Alle ausgegebenen Vault-Tokens werden ungültig."""
    with db() as c:
        c.execute("UPDATE vault_pins SET generation = generation + 1, updated_at = ? WHERE user_id = ?",
                  (_now(), user_id))
    return generation(user_id)


def _write(user_id: str, pin_hash: str | None) -> int:
    ts = _now()
    with db() as c:
        c.execute(
            """INSERT INTO vault_pins (user_id, pin_hash, generation, created_at, updated_at)
               VALUES (?, ?, 1, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET pin_hash = excluded.pin_hash,
                   generation = vault_pins.generation + 1, updated_at = excluded.updated_at""",
            (user_id, pin_hash, ts, ts),
        )
        return int(c.execute("SELECT generation FROM vault_pins WHERE user_id = ?", (user_id,)).fetchone()[0])
