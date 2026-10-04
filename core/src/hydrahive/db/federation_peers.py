"""DB-Operationen für gekoppelte HydraHive-Server (docs/specs/server-peering.md)."""
from __future__ import annotations

import uuid
from typing import Any

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

STATUSES = ("pending", "active", "blocked")


def _row(r: Any) -> dict:
    return dict(r)


def list_peers() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM federation_peers ORDER BY name").fetchall()
    return [_row(r) for r in rows]


def get_peer(peer_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM federation_peers WHERE id = ?", (peer_id,)).fetchone()
    return _row(row) if row else None


def get_by_name(name: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM federation_peers WHERE LOWER(name) = LOWER(?)", (name,),
        ).fetchone()
    return _row(row) if row else None


def get_by_public_key(public_key: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM federation_peers WHERE public_key = ?", (public_key,),
        ).fetchone()
    return _row(row) if row else None


def create_peer(name: str, url: str, public_key: str, fingerprint: str) -> dict:
    peer_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            "INSERT INTO federation_peers (id, name, url, public_key, fingerprint, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (peer_id, name, url.rstrip("/"), public_key, fingerprint, now_iso()),
        )
    return get_peer(peer_id)  # type: ignore[return-value]


def set_status(peer_id: str, status: str) -> dict | None:
    if status not in STATUSES:
        raise ValueError(f"ungültiger Status: {status}")
    confirmed = now_iso() if status == "active" else None
    with db() as conn:
        conn.execute(
            "UPDATE federation_peers SET status = ?, "
            "confirmed_at = COALESCE(?, confirmed_at) WHERE id = ?",
            (status, confirmed, peer_id),
        )
    return get_peer(peer_id)


def touch(peer_id: str) -> None:
    with db() as conn:
        conn.execute("UPDATE federation_peers SET last_seen = ? WHERE id = ?", (now_iso(), peer_id))


def delete_peer(peer_id: str) -> bool:
    with db() as conn:
        conn.execute("DELETE FROM federation_peer_agents WHERE peer_id = ?", (peer_id,))
        conn.execute("DELETE FROM federation_peer_tasks WHERE peer_id = ?", (peer_id,))
        cur = conn.execute("DELETE FROM federation_peers WHERE id = ?", (peer_id,))
    return cur.rowcount > 0


def allowed_agents(peer_id: str) -> list[str]:
    with db() as conn:
        rows = conn.execute(
            "SELECT agent_id FROM federation_peer_agents WHERE peer_id = ? ORDER BY agent_id",
            (peer_id,),
        ).fetchall()
    return [r["agent_id"] for r in rows]


def set_allowed_agents(peer_id: str, agent_ids: list[str]) -> list[str]:
    unique = sorted(set(agent_ids))
    with db() as conn:
        conn.execute("DELETE FROM federation_peer_agents WHERE peer_id = ?", (peer_id,))
        conn.executemany(
            "INSERT INTO federation_peer_agents (peer_id, agent_id) VALUES (?, ?)",
            [(peer_id, a) for a in unique],
        )
    return unique


def is_agent_allowed(peer_id: str, agent_id: str) -> bool:
    with db() as conn:
        row = conn.execute(
            "SELECT 1 FROM federation_peer_agents WHERE peer_id = ? AND agent_id = ?",
            (peer_id, agent_id),
        ).fetchone()
    return row is not None


def claim_task(task_id: str, peer_id: str, direction: str) -> bool:
    """Legt einen Auftrag an. False, wenn die ID schon bekannt ist (Replay)."""
    with db() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO federation_peer_tasks "
            "(task_id, peer_id, direction, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
            (task_id, peer_id, direction, now_iso()),
        )
    return cur.rowcount == 1


def set_task_status(task_id: str, status: str, *, local_state_id: str | None = None) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE federation_peer_tasks SET status = ?, "
            "local_state_id = COALESCE(?, local_state_id) WHERE task_id = ?",
            (status, local_state_id, task_id),
        )


def get_task(task_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM federation_peer_tasks WHERE task_id = ?", (task_id,),
        ).fetchone()
    return _row(row) if row else None
