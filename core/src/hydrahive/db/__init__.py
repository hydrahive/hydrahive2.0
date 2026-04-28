"""Database layer for HydraHive2.

SQLite-only, sync (no aiosqlite), WAL mode, FK enforced. UUIDv7 primary keys,
ISO-8601 timestamps. Migrations via files in `migrations/NNN_name.sql`.

Public API:
    init_db()                      — call once at startup
    db()                           — context manager for raw SQL
    sessions / messages / tools    — CRUD modules with dataclasses
    session_state                  — generic key/value store per session
    uuid7() / now_iso()            — id and timestamp helpers
"""

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db, init_db
from hydrahive.db import messages, sessions, state as session_state, tools

__all__ = [
    "init_db",
    "db",
    "sessions",
    "messages",
    "tools",
    "session_state",
    "uuid7",
    "now_iso",
]
