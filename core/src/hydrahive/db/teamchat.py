"""DB-Operationen für Team-Chat (Matrix-Integration).

Speichert Matrix-Identitäten, Räume und Room-Agent-Zuordnungen.
Kein Encryption-Code hier — access_token wird as-is gespeichert.
Kein Matrix/nio-Import hier.
"""
from __future__ import annotations

from typing import Any

from hydrahive.db.connection import db


def _row(r: Any) -> dict:
    return dict(r)


# ---------------------------------------------------------------------------
# Identities
# ---------------------------------------------------------------------------

def get_identity(user_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM teamchat_identities WHERE user_id = ?", (user_id,)
        ).fetchone()
    return _row(row) if row else None


def upsert_identity(
    user_id: str,
    mxid: str,
    access_token: str,
    device_id: str | None = None,
    next_batch: str | None = None,
) -> dict:
    """Legt eine Matrix-Identität an oder aktualisiert sie (Re-Provisioning).

    Nutzt INSERT ... ON CONFLICT DO UPDATE damit ein zweiter upsert-Aufruf
    immer die neuesten Werte speichert statt zu duplizieren.
    """
    with db() as conn:
        conn.execute(
            """
            INSERT INTO teamchat_identities
                (user_id, mxid, access_token, device_id, next_batch)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                mxid         = excluded.mxid,
                access_token = excluded.access_token,
                device_id    = excluded.device_id,
                next_batch   = excluded.next_batch
            """,
            (user_id, mxid, access_token, device_id, next_batch),
        )
    return get_identity(user_id)  # type: ignore[return-value]


def update_next_batch(user_id: str, next_batch: str) -> None:
    """Aktualisiert den Matrix-Sync-Cursor für einen User."""
    with db() as conn:
        conn.execute(
            "UPDATE teamchat_identities SET next_batch = ? WHERE user_id = ?",
            (next_batch, user_id),
        )


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

def get_room(room_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM teamchat_rooms WHERE room_id = ?", (room_id,)
        ).fetchone()
    return _row(row) if row else None


def create_room(room_id: str, name: str, created_by: str) -> dict:
    with db() as conn:
        conn.execute(
            "INSERT INTO teamchat_rooms (room_id, name, created_by) VALUES (?, ?, ?)",
            (room_id, name, created_by),
        )
    return get_room(room_id)  # type: ignore[return-value]


def update_room_name(room_id: str, name: str) -> None:
    """Benennt einen Raum um (HH-DB ist die für die UI sichtbare Quelle)."""
    with db() as conn:
        conn.execute(
            "UPDATE teamchat_rooms SET name = ? WHERE room_id = ?", (name, room_id)
        )


def delete_room(room_id: str) -> None:
    """Entfernt einen Raum + seine Agent-Zuordnungen aus der HH-DB.

    Die Matrix-Hülle bleibt verwaist — Matrix kennt kein echtes Raum-Löschen;
    aus HH-Sicht (list_joined_rooms ∩ DB) verschwindet der Raum für alle.
    """
    with db() as conn:
        conn.execute("DELETE FROM teamchat_room_agents WHERE room_id = ?", (room_id,))
        conn.execute("DELETE FROM teamchat_rooms WHERE room_id = ?", (room_id,))


def list_rooms_for_user(user_id: str) -> list[dict]:
    """Gibt alle bekannten Räume zurück, sortiert nach created_at.

    Hinweis: Die eigentliche Raum-Mitgliedschaft liegt in Matrix, nicht in
    dieser DB. Der user_id-Parameter wird für Vorwärts-Kompatibilität
    akzeptiert, hat aber aktuell keinen Filtereffekt.
    """
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM teamchat_rooms ORDER BY created_at"
        ).fetchall()
    return [_row(r) for r in rows]


# ---------------------------------------------------------------------------
# Room-Agent-Zuordnungen
# ---------------------------------------------------------------------------

def attach_agent(room_id: str, agent_id: str, attached_by: str) -> None:
    """Weist einem Raum einen Agenten zu. Idempotent."""
    with db() as conn:
        conn.execute(
            """
            INSERT INTO teamchat_room_agents (room_id, agent_id, attached_by)
            VALUES (?, ?, ?)
            ON CONFLICT(room_id, agent_id) DO NOTHING
            """,
            (room_id, agent_id, attached_by),
        )


def detach_agent(room_id: str, agent_id: str) -> None:
    """Entfernt einen Agenten aus einem Raum."""
    with db() as conn:
        conn.execute(
            "DELETE FROM teamchat_room_agents WHERE room_id = ? AND agent_id = ?",
            (room_id, agent_id),
        )


def list_room_agents(room_id: str) -> list[dict]:
    """Gibt alle Agenten eines Raums zurück, sortiert nach attached_at."""
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM teamchat_room_agents WHERE room_id = ? ORDER BY attached_at",
            (room_id,),
        ).fetchall()
    return [_row(r) for r in rows]
