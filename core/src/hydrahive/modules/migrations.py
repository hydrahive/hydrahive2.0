"""Per-Modul-Migrationen — eigene Versions-Tabelle, getrennt vom Core."""
from __future__ import annotations
import logging
import sqlite3
from pathlib import Path
from hydrahive.db.connection import db
from hydrahive.db._utils import now_iso

logger = logging.getLogger(__name__)


def _current(conn: sqlite3.Connection, module_id: str) -> int:
    row = conn.execute(
        "SELECT MAX(version) FROM module_schema_version WHERE module_id = ?", (module_id,)
    ).fetchone()
    return (row[0] if row else 0) or 0


def apply_module_migrations(module_id: str, migrations_dir: Path) -> None:
    """Wendet ausstehende NNN_*.sql des Moduls an, trackt pro Modul.
    Deinstall ruft das NICHT rückwärts — Daten bleiben."""
    migrations_dir = Path(migrations_dir)
    if not migrations_dir.is_dir():
        return
    with db() as conn:
        current = _current(conn, module_id)
        for f in sorted(migrations_dir.glob("*.sql")):
            try:
                version = int(f.name.split("_", 1)[0])
            except ValueError:
                logger.warning("Modul %s: Migration %s ohne Versions-Prefix — übersprungen", module_id, f.name)
                continue
            if version <= current:
                continue
            try:
                conn.executescript(f.read_text())
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc) and "already exists" not in str(exc):
                    raise
                logger.warning("Modul %s: Migration %s bereits partiell — markiere als erledigt (%s)", module_id, f.name, exc)
            conn.execute(
                "INSERT OR IGNORE INTO module_schema_version (module_id, version, applied_at) VALUES (?, ?, ?)",
                (module_id, version, now_iso()),
            )
            logger.info("Modul %s: Migration %s angewendet (v%d)", module_id, f.name, version)
