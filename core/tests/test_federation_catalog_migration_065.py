"""G3/P1 — Migration 065: Tabelle federation_catalog_project_map, wiederholbar."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from hydrahive.db.connection import db

SQL = Path(__file__).resolve().parents[1] / "src/hydrahive/db/migrations/065_federation_project_map.sql"


def test_tabelle_mit_schluessel(client):
    with db() as conn:
        cols = {r["name"]: r for r in conn.execute("PRAGMA table_info(federation_catalog_project_map)")}
    assert set(cols) == {"username", "origin_fp", "origin_project_id", "target", "updated_at"}
    assert [n for n, r in sorted(cols.items(), key=lambda x: x[1]["pk"]) if r["pk"]] == [
        "username", "origin_fp", "origin_project_id"]


def test_frisch_und_zweiter_lauf_aendern_nichts():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SQL.read_text())
    conn.execute("INSERT INTO federation_catalog_project_map VALUES ('u', 'fp', 'p', 'hidden', 'x')")
    conn.executescript(SQL.read_text())                       # zweiter Lauf
    assert conn.execute("SELECT COUNT(*) FROM federation_catalog_project_map").fetchone()[0] == 1


def test_tabelle_fuer_den_stand_der_urspruenge(client):
    with db() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(federation_catalog_mirror_instances)")}
    assert cols == {"origin_fp", "origin_name", "last_seen", "stale", "received_at"}
