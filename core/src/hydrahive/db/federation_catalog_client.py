"""Client-Seite des Föderations-Katalogs: Versand-Zustand.

docs/specs/federation-catalog.md §Datenmodell (Client-Seite) und §Ablauf 2:
laufende ``seq``, Cursor je Nutzer und Art, Status (``last_push_at``,
``last_ok_at``, ``last_full_at``, ``last_error``) einmal in
``federation_catalog_settings``. Nur lesen/schreiben, kein Netz.
"""
from __future__ import annotations

from dataclasses import dataclass

from hydrahive.db.connection import db

_UNSET = object()


@dataclass(frozen=True)
class SyncConfig:
    enabled: bool
    interval_seconds: int
    hub: dict | None          # Partnerzeile (url, public_key, status, …) oder None
    users: tuple[str, ...]
    excluded_projects: frozenset[str]
    last_full_at: str | None
    # Gemeinsame Taskpflege (docs/specs/federation-shared-tasks.md §Schalter),
    # Standard aus. Werden in jedem catalog_push mitgemeldet (new_catalog_push).
    shared: bool = False
    remote_edits: bool = False

    @property
    def active(self) -> bool:
        """Nur dann darf überhaupt Netzverkehr entstehen."""
        return self.enabled and bool(self.users) and bool(self.hub) and self.hub.get("status") == "active"


def load_config() -> SyncConfig:
    with db() as conn:
        row = conn.execute(
            "SELECT enabled, interval_seconds, last_full_at, shared, remote_edits "
            "FROM federation_catalog_settings WHERE id = 1",
        ).fetchone()
        hub = conn.execute("SELECT * FROM federation_peers WHERE is_hub = 1 LIMIT 1").fetchone()
        users = conn.execute("SELECT username FROM federation_catalog_users ORDER BY username").fetchall()
        excluded = conn.execute("SELECT project_id FROM federation_catalog_excluded_projects").fetchall()
    return SyncConfig(
        enabled=bool(row and row["enabled"]),
        interval_seconds=int(row["interval_seconds"]) if row and row["interval_seconds"] else 300,
        hub=dict(hub) if hub else None,
        users=tuple(r["username"] for r in users),
        excluded_projects=frozenset(r["project_id"] for r in excluded),
        last_full_at=row["last_full_at"] if row else None,
        shared=bool(row and row["shared"]),
        remote_edits=bool(row and row["remote_edits"]),
    )


def next_seq() -> int:
    """Nächste ``seq`` atomar vergeben (streng steigend, auch wenn der Versand scheitert)."""
    with db(immediate=True) as conn:
        conn.execute("INSERT OR IGNORE INTO federation_catalog_settings (id) VALUES (1)")
        conn.execute("UPDATE federation_catalog_settings SET seq = seq + 1 WHERE id = 1")
        return int(conn.execute("SELECT seq FROM federation_catalog_settings WHERE id = 1").fetchone()[0])


def raise_seq_to(value: int) -> None:
    """Nach ``peer_replay`` (z. B. Backup-Restore): auf den Stand des Hubs springen."""
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO federation_catalog_settings (id) VALUES (1)")
        conn.execute("UPDATE federation_catalog_settings SET seq = MAX(seq, ?) WHERE id = 1", (int(value),))


def get_cursors() -> dict[tuple[str, str], str | None]:
    with db() as conn:
        rows = conn.execute("SELECT username, kind, cursor_updated_at FROM federation_catalog_cursors").fetchall()
    return {(r["username"], r["kind"]): r["cursor_updated_at"] for r in rows}


def set_cursors(values: dict[tuple[str, str], str]) -> None:
    """Cursor erst nach vollständig bestätigtem Lauf setzen (nie rückwärts)."""
    with db() as conn:
        conn.executemany(
            "INSERT INTO federation_catalog_cursors (username, kind, cursor_updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT (username, kind) DO UPDATE SET cursor_updated_at = CASE "
            "WHEN federation_catalog_cursors.cursor_updated_at IS NULL "
            "  OR excluded.cursor_updated_at > federation_catalog_cursors.cursor_updated_at "
            "THEN excluded.cursor_updated_at ELSE federation_catalog_cursors.cursor_updated_at END",
            [(u, k, v) for (u, k), v in values.items()],
        )


def reset_cursors(pairs: list[tuple[str, str]]) -> None:
    """``resync`` vom Hub: diese Paare im nächsten Lauf vollständig schicken."""
    with db() as conn:
        conn.executemany(
            "DELETE FROM federation_catalog_cursors WHERE username = ? AND kind = ?", pairs,
        )


def record_status(*, push_at=_UNSET, ok_at=_UNSET, full_at=_UNSET, error=_UNSET) -> None:
    fields = {k: v for k, v in (
        ("last_push_at", push_at), ("last_ok_at", ok_at), ("last_full_at", full_at), ("last_error", error),
    ) if v is not _UNSET}
    if not fields:
        return
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO federation_catalog_settings (id) VALUES (1)")
        conn.execute(
            f"UPDATE federation_catalog_settings SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = 1",
            list(fields.values()),
        )
