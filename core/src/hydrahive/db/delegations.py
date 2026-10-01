"""Hintergrund-Aufträge an Spezialisten (docs/specs/agent-background-delegation.md).

Statusmodell: Nur `running → *` ist erlaubt (UPDATE … WHERE status='running').
Wer zuerst schreibt, gewinnt: Receiver (gleicher Prozess), AgentLink-Antwort,
Timeout oder Abbruch. Zustellen = `delivered_at` atomar setzen (claim).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

FINISHED = ("done", "error", "paused", "timeout", "lost")
TASK_MAX_CHARS = 500


def create(
    *, session_id: str, agent_id: str, user_id: str, target_agent_id: str,
    target_name: str, task: str, state_id: str, depth: int, timeout_seconds: int,
) -> dict:
    row_id = uuid7()
    now = datetime.now(timezone.utc)
    deadline = (now + timedelta(seconds=timeout_seconds)).isoformat(timespec="milliseconds")
    with db() as conn:
        conn.execute(
            """INSERT INTO agent_delegations
               (id, session_id, agent_id, user_id, target_agent_id, target_name,
                task, state_id, depth, status, created_at, deadline_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)""",
            (row_id, session_id, agent_id, user_id, target_agent_id, target_name,
             task[:TASK_MAX_CHARS], state_id, depth,
             now.isoformat(timespec="milliseconds"), deadline),
        )
    return get(row_id)  # type: ignore[return-value]


def get(delegation_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM agent_delegations WHERE id = ?", (delegation_id,),
        ).fetchone()
    return dict(row) if row else None


def get_by_state(state_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM agent_delegations WHERE state_id = ?", (state_id,),
        ).fetchone()
    return dict(row) if row else None


def target_session_id(state_id: str) -> str | None:
    """Session des Spezialisten — agent_handoffs kennt sie über den Auftrags-State."""
    with db() as conn:
        row = conn.execute(
            """SELECT session_id FROM agent_handoffs WHERE incoming_state_id = ?
               ORDER BY started_at DESC LIMIT 1""",
            (state_id,),
        ).fetchone()
    return row[0] if row else None


def complete_if_running(delegation_id: str, status: str, result: str | None) -> bool:
    """running → status. False, wenn jemand anderes schneller war."""
    with db() as conn:
        cur = conn.execute(
            """UPDATE agent_delegations SET status = ?, result = ?, finished_at = ?
               WHERE id = ? AND status = 'running'""",
            (status, result, now_iso(), delegation_id),
        )
    return cur.rowcount == 1


def complete_by_state(state_id: str, status: str, result: str | None) -> dict | None:
    """Vom handoff_receiver nach Lauf-Ende. Liefert die Delegation, wenn sie
    durch diesen Aufruf abgeschlossen wurde."""
    row = get_by_state(state_id)
    if row and complete_if_running(row["id"], status, result):
        return get(row["id"])
    return None


def count_running(session_id: str) -> int:
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM agent_delegations WHERE session_id = ? AND status = 'running'",
            (session_id,),
        ).fetchone()
    return int(row[0])


def has_undelivered(session_id: str) -> bool:
    marks = ",".join("?" * len(FINISHED))
    with db() as conn:
        row = conn.execute(
            f"""SELECT 1 FROM agent_delegations WHERE session_id = ?
                AND status IN ({marks}) AND delivered_at IS NULL LIMIT 1""",
            (session_id, *FINISHED),
        ).fetchone()
    return row is not None


def claim_undelivered(session_id: str) -> list[dict]:
    """Alle fertigen, noch nicht zugestellten Delegationen atomar beanspruchen.
    `cancelled` wird nie zugestellt (der Nutzer hat bewusst abgebrochen)."""
    marks = ",".join("?" * len(FINISHED))
    now = now_iso()
    with db(immediate=True) as conn:
        rows = conn.execute(
            f"""SELECT * FROM agent_delegations WHERE session_id = ?
                AND status IN ({marks}) AND delivered_at IS NULL
                ORDER BY finished_at, created_at""",
            (session_id, *FINISHED),
        ).fetchall()
        ids = [r["id"] for r in rows]
        if ids:
            conn.execute(
                f"UPDATE agent_delegations SET delivered_at = ? WHERE id IN ({','.join('?' * len(ids))})",
                (now, *ids),
            )
    return [dict(r) for r in rows]


def unclaim(ids: list[str]) -> None:
    """Zustellung fehlgeschlagen (z. B. Session lief inzwischen) → später erneut."""
    if not ids:
        return
    with db() as conn:
        conn.execute(
            f"UPDATE agent_delegations SET delivered_at = NULL WHERE id IN ({','.join('?' * len(ids))})",
            ids,
        )


def list_for_session(session_id: str, limit: int = 20) -> list[dict]:
    """Neueste zuerst, mit Session des Spezialisten (aus agent_handoffs)."""
    with db() as conn:
        rows = conn.execute(
            """SELECT d.*, (SELECT h.session_id FROM agent_handoffs h
                            WHERE h.incoming_state_id = d.state_id
                            ORDER BY h.started_at DESC LIMIT 1) AS target_session_id
               FROM agent_delegations d WHERE d.session_id = ?
               ORDER BY d.created_at DESC LIMIT ?""",
            (session_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def sessions_with_undelivered() -> list[str]:
    marks = ",".join("?" * len(FINISHED))
    with db() as conn:
        rows = conn.execute(
            f"""SELECT DISTINCT session_id FROM agent_delegations
                WHERE status IN ({marks}) AND delivered_at IS NULL""",
            FINISHED,
        ).fetchall()
    return [r[0] for r in rows]


def reconcile_on_start() -> int:
    """Beim Start: Was noch 'running' ist, hat keinen Watcher mehr → 'lost'."""
    with db() as conn:
        cur = conn.execute(
            """UPDATE agent_delegations
               SET status = 'lost', finished_at = ?,
                   result = 'Der Server wurde neu gestartet, bevor das Ergebnis eintraf.'
               WHERE status = 'running'""",
            (now_iso(),),
        )
    return cur.rowcount
