from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from hydrahive.db._utils import now_iso

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


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
        sql = f.read_text()
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
            (version, now_iso()),
        )
        conn.commit()
        applied += 1
        logger.info("Migration %s angewendet (Version %d)", f.name, version)
    if applied == 0:
        logger.debug("Keine neuen Migrations (aktuelle Version: %d)", current)
