"""Audit für Pool-, Freigabe- und Bestätigungsänderungen: dasselbe Log wie die übrigen Admin-Aktionen (``access_audit``).

Der Eintrag entsteht in der Transaktion der Änderung (wie ``access.store``); abgelehnte Änderungen schreiben nichts.
"""
from __future__ import annotations

import sqlite3

from hydrahive.access.store import audit


def _actor_id(username: str) -> str:
    from hydrahive.api.middleware.users import get_by_username
    user = get_by_username(username) if username else None
    return (user or {}).get("user_id") or username


def log(conn: sqlite3.Connection, actor: str, action: str, target: str, items: list[str]) -> None:
    audit(conn, _actor_id(actor), action, target, ", ".join(items) or "(leer)")
