from __future__ import annotations

import logging
import re
import sqlite3
from collections.abc import Callable
from pathlib import Path

from hydrahive.db._utils import now_iso

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Dateien mit eigener Transaktionssteuerung (z. B. 062/064/065) oder mit Anweisungen, die in einer Transaktion nicht
# wirken bzw. nicht erlaubt sind (PRAGMA foreign_keys=OFF vor DROP TABLE – sonst greift ON DELETE CASCADE –, VACUUM,
# ATTACH), laufen wie bisher ohne äußere Transaktion. Trigger-Rümpfe („BEGIN" ohne direktes „;") zählen nicht.
_NOT_WRAPPABLE = re.compile(
    r"^\s*(?:(?:BEGIN|COMMIT|ROLLBACK)(?:\s+(?:DEFERRED|IMMEDIATE|EXCLUSIVE))?(?:\s+TRANSACTION)?\s*;"
    r"|(?:PRAGMA|VACUUM|ATTACH|DETACH)\b)",
    re.IGNORECASE | re.MULTILINE,
)


def run_migration_script(conn: sqlite3.Connection, sql: str, label: str, record: Callable[[], None]) -> None:
    """Führt eine Migrations-Datei aus und verbucht sie über ``record`` (Versionszeile), dann COMMIT.

    Atomar: Ohne eigene Transaktionssteuerung läuft die Datei samt Versionszeile in EINER Transaktion. Scheitert
    sie, wird alles zurückgerollt und der Fehler weitergereicht – es bleibt kein halber Stand zurück, den ein
    späterer Start fälschlich als „bereits partiell angewendet“ verbuchen könnte (Probe U4P, 23.11.2026).

    „already exists“/„duplicate column name“ gelten weiter als bereits vorhanden (Objekt außerhalb der Migration
    angelegt, Verhalten wie seit 858cb143).
    """
    wrapped = not _NOT_WRAPPABLE.search(sql)
    try:
        conn.executescript(("BEGIN;\n" + sql) if wrapped else sql)
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc) and "already exists" not in str(exc):
            if conn.in_transaction:
                conn.rollback()
            raise
        logger.warning("Migration %s bereits partiell angewendet (%s) — überspringe", label, exc)
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    record()
    conn.commit()


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_version (
               version    INTEGER PRIMARY KEY,
               applied_at TEXT NOT NULL
           )"""
    )


def current_version(conn: sqlite3.Connection) -> int:
    _ensure_version_table(conn)
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return (row[0] if row else 0) or 0


def apply_migrations(conn: sqlite3.Connection) -> None:
    current = current_version(conn)
    if not MIGRATIONS_DIR.exists():
        logger.warning("Keine Migrations gefunden in %s", MIGRATIONS_DIR)
        return
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    applied = 0
    for f in files:
        try:
            version = int(f.name.split("_", 1)[0])
        except ValueError:
            logger.warning("Ignoriere Migrations-Datei mit ungültigem Namen: %s", f.name)
            continue
        if version <= current:
            continue
        run_migration_script(
            conn, f.read_text(), f.name,
            lambda v=version: conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)", (v, now_iso()),
            ),
        )
        applied += 1
        logger.info("Migration %s angewendet (Version %d)", f.name, version)
    if applied == 0:
        logger.debug("Keine neuen Migrations (aktuelle Version: %d)", current)
