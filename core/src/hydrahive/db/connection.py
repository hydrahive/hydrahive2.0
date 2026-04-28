from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from hydrahive.db.migrations import apply_migrations
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Set up the SQLite file (WAL mode, FK on) and run migrations.

    Idempotent — safe to call on every backend start.
    """
    settings.sessions_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.sessions_db)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA synchronous = NORMAL")
        apply_migrations(conn)
    finally:
        conn.close()
    logger.info("DB bereit: %s", settings.sessions_db)


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    """Per-call connection with FK enforcement and automatic commit/rollback."""
    conn = sqlite3.connect(settings.sessions_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
