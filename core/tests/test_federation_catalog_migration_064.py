"""V1 — Migration 064_federation_shared.sql (docs/specs/federation-shared-tasks.md
§Datenmodell). Nur Tabellen/Spalten für G2 (shared/remote_edits, rev-Zähler,
Löschprotokoll, Client-Kopie). Noch keine Verteilungslogik.

Muster wie test_federation_catalog_migration.py (062/063): frisch, bestehend
mit Altbestand (Backfill), zweiter Lauf ist ein No-op.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from hydrahive.db.migrations import MIGRATIONS_DIR, apply_migrations, current_version


def _apply_through(conn: sqlite3.Connection, maximum: int) -> None:
    current_version(conn)
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


def test_migration_064_on_fresh_db(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "fresh.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        apply_migrations(conn)
        assert current_version(conn) >= 64

        for table in (
            "federation_catalog_counter",
            "federation_catalog_deletions",
            "federation_catalog_mirror",
        ):
            conn.execute(f"SELECT * FROM {table}")

        settings_cols = {r["name"] for r in conn.execute("PRAGMA table_info(federation_catalog_settings)")}
        assert {
            "shared", "remote_edits", "pull_rev", "pull_local_cursor",
            "last_pull_at", "last_pull_error", "last_full_pull_at",
        } <= settings_cols

        sources_cols = {r["name"] for r in conn.execute("PRAGMA table_info(federation_catalog_sources)")}
        assert {"shared", "remote_edits", "pull_users", "last_pull_at", "reset_local"} <= sources_cols

        items_cols = {r["name"] for r in conn.execute("PRAGMA table_info(federation_catalog_items)")}
        assert "rev" in items_cols

        counter = conn.execute("SELECT rev, purged_rev FROM federation_catalog_counter WHERE id = 1").fetchone()
        assert counter["rev"] == 0
        assert counter["purged_rev"] == 0
    finally:
        conn.close()


def test_migration_064_second_run_is_noop(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "fresh.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        apply_migrations(conn)
        before_schema = _snapshot(conn)
        before_version = current_version(conn)

        apply_migrations(conn)

        assert _snapshot(conn) == before_schema
        assert current_version(conn) == before_version >= 64
    finally:
        conn.close()


def test_migration_064_backfills_rev_on_existing_items(tmp_path: Path) -> None:
    """Altbestand in federation_catalog_items (Stand <=063) bekommt eine
    eindeutige rev > 0 nach rowid, der Zähler steht danach auf dem Maximum."""
    conn = sqlite3.connect(tmp_path / "existing.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _apply_through(conn, 63)
        conn.execute(
            "INSERT INTO federation_peers (id, name, url, public_key, fingerprint, status, created_at) "
            "VALUES ('p1', 'hydrahome', 'https://x', 'k', 'f', 'active', 'now')",
        )
        for item_id, title in (("t1", "Erstes"), ("t2", "Zweites"), ("t3", "Drittes")):
            conn.execute(
                "INSERT INTO federation_catalog_items "
                "(peer_id, kind, item_id, owner, title, status, received_at) "
                "VALUES ('p1', 'task', ?, 'till', ?, 'open', 'now')",
                (item_id, title),
            )
        conn.commit()

        apply_migrations(conn)

        assert current_version(conn) >= 64
        rows = conn.execute("SELECT rev FROM federation_catalog_items ORDER BY rev").fetchall()
        revs = [r["rev"] for r in rows]
        assert len(revs) == 3
        assert all(r > 0 for r in revs)
        assert len(set(revs)) == 3  # eindeutig

        counter = conn.execute("SELECT rev FROM federation_catalog_counter WHERE id = 1").fetchone()
        assert counter["rev"] == max(revs)
    finally:
        conn.close()


def test_migration_064_abort_mid_alter_leaves_nothing(tmp_path: Path) -> None:
    """Simuliert einen Abbruch mitten in den ALTERs: die Transaktion wird nicht
    committet, also bleibt beim nächsten Lauf nichts Halbes zurück."""
    conn = sqlite3.connect(tmp_path / "abort.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _apply_through(conn, 63)
        before = _snapshot(conn)

        sql = (MIGRATIONS_DIR / "064_federation_shared.sql").read_text()
        truncated = sql.split("ALTER TABLE federation_catalog_sources ADD COLUMN remote_edits", 1)[0]
        try:
            conn.executescript(truncated)
        except sqlite3.OperationalError:
            pass
        conn.rollback()

        assert _snapshot(conn) == before  # nichts von der Teil-Ausführung übrig

        apply_migrations(conn)
        assert current_version(conn) >= 64
        settings_cols = {r["name"] for r in conn.execute("PRAGMA table_info(federation_catalog_settings)")}
        assert "remote_edits" in settings_cols
    finally:
        conn.close()
