"""SQLite FTS5-Index + Backlink-Tabelle für HydraWiki.

Der Index ist regenerierbar — einzige Source of Truth sind die .md-Dateien.
rebuild() baut ihn komplett neu aus dem Filesystem.
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from hydrahive.settings import settings
from hydrahive.wiki.models import WikiPage

_lock = threading.Lock()


def _db_path() -> Path:
    return settings.data_dir / "wiki.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock, _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pages (
                slug TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                tags TEXT,
                entities TEXT,
                author TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
                slug UNINDEXED, title, body,
                content='', tokenize='unicode61'
            );
            CREATE TABLE IF NOT EXISTS backlinks (
                from_slug TEXT NOT NULL,
                to_slug TEXT NOT NULL,
                PRIMARY KEY (from_slug, to_slug)
            );
        """)


def upsert(page: WikiPage) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?)",
            (page.slug, page.title, ",".join(page.tags), ",".join(page.entities),
             page.author, page.created_at, page.updated_at),
        )
        conn.execute("DELETE FROM pages_fts WHERE slug = ?", (page.slug,))
        conn.execute(
            "INSERT INTO pages_fts(slug, title, body) VALUES (?,?,?)",
            (page.slug, page.title, page.body),
        )
        conn.execute("DELETE FROM backlinks WHERE from_slug = ?", (page.slug,))
        for target in page.outgoing_links():
            conn.execute(
                "INSERT OR IGNORE INTO backlinks VALUES (?,?)",
                (page.slug, target),
            )


def remove(slug: str) -> None:
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM pages WHERE slug = ?", (slug,))
        conn.execute("DELETE FROM pages_fts WHERE slug = ?", (slug,))
        conn.execute("DELETE FROM backlinks WHERE from_slug = ? OR to_slug = ?",
                     (slug, slug))


def search(query: str, limit: int = 50) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT p.slug, p.title, p.tags, p.author, p.updated_at,
                      snippet(pages_fts, 2, '<b>', '</b>', '…', 20) AS snippet
               FROM pages_fts f
               JOIN pages p ON p.slug = f.slug
               WHERE pages_fts MATCH ?
               ORDER BY rank LIMIT ?""",
            (query, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def backlinks_for(slug: str) -> list[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT from_slug FROM backlinks WHERE to_slug = ?", (slug,)
        ).fetchall()
    return [r["from_slug"] for r in rows]


def rebuild() -> None:
    from hydrahive.wiki import storage
    with _lock, _connect() as conn:
        conn.executescript(
            "DELETE FROM pages; DELETE FROM pages_fts; DELETE FROM backlinks;"
        )
    for page in storage.list_all():
        upsert(page)
