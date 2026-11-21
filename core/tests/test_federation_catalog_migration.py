"""E1 — Migration 062_federation_catalog.sql (docs/specs/federation-catalog.md).

Läuft auf frischer DB und auf bestehender DB (Stand <=061 mit vorhandenem
Partner) fehlerfrei; ein zweiter Lauf von apply_migrations ändert nichts
mehr (Schema unverändert, schema_version unverändert). Muster wie
test_compute_game_jobs_migration.py::_apply_through.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from hydrahive.db.migrations import MIGRATIONS_DIR, apply_migrations, current_version


def _apply_through(conn: sqlite3.Connection, maximum: int) -> None:
    current_version(conn)  # legt schema_version an, falls noch nicht vorhanden
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = int(migration.name.split("_", 1)[0])
        if version > maximum:
            break
        conn.executescript(migration.read_text())
        conn.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
            (version, "now"),
        )
    conn.commit()


def _snapshot(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE type IN ('table', 'index', 'trigger') ORDER BY name",
    ).fetchall()
    return {f"{r[0]}:{r[1]}:{r[2]}" for r in rows}


def test_migration_062_on_fresh_db(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "fresh.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        apply_migrations(conn)
        assert current_version(conn) == 62

        cols = {row["name"] for row in conn.execute("PRAGMA table_info(federation_peers)")}
        assert {"is_hub", "catalog_accept"} <= cols

        for table in (
            "federation_catalog_settings",
            "federation_catalog_users",
            "federation_catalog_excluded_projects",
            "federation_catalog_cursors",
            "federation_catalog_items",
            "federation_catalog_fts",
            "federation_catalog_rejected",
            "federation_catalog_sources",
        ):
            conn.execute(f"SELECT * FROM {table}")  # löst OperationalError, wenn fehlend
    finally:
        conn.close()


def test_migration_062_second_run_is_noop(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "fresh.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        apply_migrations(conn)
        before_schema = _snapshot(conn)
        before_version = current_version(conn)

        apply_migrations(conn)

        assert _snapshot(conn) == before_schema
        assert current_version(conn) == before_version == 62
    finally:
        conn.close()


def test_migration_062_on_existing_db_with_peer(tmp_path: Path) -> None:
    """Bestehende DB mit Stand <=061 und schon vorhandenem Partner."""
    conn = sqlite3.connect(tmp_path / "existing.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _apply_through(conn, 61)
        conn.execute(
            "INSERT INTO federation_peers "
            "(id, name, url, public_key, fingerprint, status, created_at) "
            "VALUES ('p1', 'vps', 'https://vps.example', 'pubkey', 'fp123', 'active', 'now')",
        )
        conn.commit()

        apply_migrations(conn)

        assert current_version(conn) == 62
        peer = conn.execute(
            "SELECT is_hub, catalog_accept FROM federation_peers WHERE id = 'p1'",
        ).fetchone()
        assert peer["is_hub"] == 0
        assert peer["catalog_accept"] == 0
    finally:
        conn.close()


def test_migration_062_fts_trigger_follows_cascade_delete(tmp_path: Path) -> None:
    """Löschung eines Partners (ON DELETE CASCADE) räumt auch die FTS-Zeile ab."""
    conn = sqlite3.connect(tmp_path / "fts.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        apply_migrations(conn)
        conn.execute(
            "INSERT INTO federation_peers "
            "(id, name, url, public_key, fingerprint, status, created_at) "
            "VALUES ('p1', 'vps', 'https://vps.example', 'pubkey', 'fp123', 'active', 'now')",
        )
        conn.execute(
            "INSERT INTO federation_catalog_items "
            "(peer_id, kind, item_id, owner, title, status, received_at) "
            "VALUES ('p1', 'task', 't1', 'till', 'Testtitel', 'open', 'now')",
        )
        conn.commit()
        assert conn.execute(
            "SELECT title FROM federation_catalog_fts WHERE federation_catalog_fts MATCH 'Testtitel'",
        ).fetchone()

        conn.execute("DELETE FROM federation_peers WHERE id = 'p1'")
        conn.commit()

        assert conn.execute("SELECT * FROM federation_catalog_items").fetchall() == []
        assert conn.execute(
            "SELECT title FROM federation_catalog_fts WHERE federation_catalog_fts MATCH 'Testtitel'",
        ).fetchone() is None
    finally:
        conn.close()
