"""Per-Modul-Migrationen — eigene Versions-Tabelle, getrennt vom Core."""
from __future__ import annotations
import logging
import sqlite3
from pathlib import Path
from hydrahive.db.connection import db
from hydrahive.db._utils import now_iso
from hydrahive.db.migrations import run_migration_script

logger = logging.getLogger(__name__)


def _current(conn: sqlite3.Connection, module_id: str) -> int:
    row = conn.execute(
        "SELECT MAX(version) FROM module_schema_version WHERE module_id = ?", (module_id,)
    ).fetchone()
    return (row[0] if row else 0) or 0


def _ensure_module_version_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS module_schema_version (
               module_id   TEXT NOT NULL,
               version     INTEGER NOT NULL,
               applied_at  TEXT NOT NULL,
               PRIMARY KEY (module_id, version)
           )"""
    )


def apply_module_migrations(module_id: str, migrations_dir: str | Path) -> None:
    """Wendet ausstehende NNN_*.sql des Moduls an, trackt pro Modul.
    Deinstall ruft das NICHT rückwärts — Daten bleiben."""
    migrations_dir = Path(migrations_dir)
    if not migrations_dir.is_dir():
        return
    with db() as conn:
        _ensure_module_version_table(conn)
        current = _current(conn, module_id)
        for f in sorted(migrations_dir.glob("*.sql")):
            try:
                version = int(f.name.split("_", 1)[0])
            except ValueError:
                logger.warning("Modul %s: Migration %s ohne Versions-Prefix — übersprungen", module_id, f.name)
                continue
            if version <= current:
                continue
            # Atomar samt Versionszeile (siehe run_migration_script); scheitert die Datei, bleibt nichts halb stehen.
            run_migration_script(
                conn, f.read_text(), f"Modul {module_id}: {f.name}",
                lambda v=version: conn.execute(
                    "INSERT OR IGNORE INTO module_schema_version (module_id, version, applied_at) VALUES (?, ?, ?)",
                    (module_id, v, now_iso()),
                ),
            )
            logger.info("Modul %s: Migration %s angewendet (v%d)", module_id, f.name, version)
