"""SQLite persistence and atomic claiming for scheduled tasks."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db
from hydrahive.schedules.models import ScheduledRun, ScheduledTask


def _task(row: sqlite3.Row) -> ScheduledTask:
    return ScheduledTask(
        task_id=row["task_id"], owner=row["owner"], scope=row["scope"],
        project_id=row["project_id"], target_type=row["target_type"], target_id=row["target_id"],
        title=row["title"], prompt=row["prompt"], execution_mode=row["execution_mode"],
        interval_seconds=row["interval_seconds"], enabled=bool(row["enabled"]),
        running=bool(row["running"]), next_run_at=row["next_run_at"],
        last_run_at=row["last_run_at"], last_status=row["last_status"],
        last_error=row["last_error"], failure_count=row["failure_count"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


def _run(row: sqlite3.Row) -> ScheduledRun:
    return ScheduledRun(
        run_id=row["run_id"], task_id=row["task_id"], started_at=row["started_at"],
        finished_at=row["finished_at"], status=row["status"],
        session_id=row["session_id"], error=row["error"],
    )


def count_enabled(owner: str) -> int:
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM scheduled_agent_tasks WHERE owner = ? AND enabled = 1",
            (owner,),
        ).fetchone()
    return int(row["count"] if row else 0)


def create(*, owner: str, scope: str, project_id: str | None, target_type: str,
           target_id: str, title: str, prompt: str, execution_mode: str,
           interval_seconds: int, enabled: bool = True) -> ScheduledTask:
    task_id, timestamp = uuid7(), now_iso()
    next_run = (datetime.now(UTC) + timedelta(seconds=interval_seconds)).isoformat().replace("+00:00", "Z")
    with db() as conn:
        conn.execute(
            """INSERT INTO scheduled_agent_tasks
               (task_id, owner, scope, project_id, target_type, target_id, title, prompt,
                execution_mode, interval_seconds, enabled, next_run_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, owner, scope, project_id, target_type, target_id, title, prompt,
             execution_mode, interval_seconds, int(enabled), next_run, timestamp, timestamp),
        )
    return get(task_id)  # type: ignore[return-value]


def get(task_id: str) -> ScheduledTask | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM scheduled_agent_tasks WHERE task_id = ?", (task_id,)).fetchone()
    return _task(row) if row else None


def list_(owner: str | None = None, project_id: str | None = None) -> list[ScheduledTask]:
    clauses, values = [], []
    if owner is not None:
        clauses.append("owner = ?"); values.append(owner)
    if project_id is not None:
        clauses.append("project_id = ?"); values.append(project_id)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with db() as conn:
        rows = conn.execute(f"SELECT * FROM scheduled_agent_tasks{where} ORDER BY created_at DESC", values).fetchall()
    return [_task(row) for row in rows]


def update(task_id: str, **changes: object) -> ScheduledTask | None:
    allowed = {"title", "prompt", "execution_mode", "interval_seconds", "enabled", "project_id", "target_id", "target_type"}
    changes = {k: v for k, v in changes.items() if k in allowed}
    if not changes:
        return get(task_id)
    fields, values = [], []
    for key, value in changes.items():
        fields.append(f"{key} = ?")
        values.append(int(value) if key == "enabled" else value)
    if "interval_seconds" in changes:
        task = get(task_id)
        if task:
            next_run = (datetime.now(UTC) + timedelta(seconds=int(changes["interval_seconds"]))).isoformat().replace("+00:00", "Z")
            fields.append("next_run_at = ?"); values.append(next_run)
    fields.extend(("updated_at = ?",))
    values.extend((now_iso(), task_id))
    with db() as conn:
        conn.execute(f"UPDATE scheduled_agent_tasks SET {', '.join(fields)} WHERE task_id = ?", values)
    return get(task_id)


def delete(task_id: str) -> bool:
    with db() as conn:
        cur = conn.execute("DELETE FROM scheduled_agent_tasks WHERE task_id = ?", (task_id,))
    return cur.rowcount > 0


def claim_due(limit: int = 16) -> list[tuple[ScheduledTask, str]]:
    now = datetime.now(UTC)
    timestamp = now.isoformat().replace("+00:00", "Z")
    with db(immediate=True) as conn:
        rows = conn.execute(
            """SELECT * FROM scheduled_agent_tasks
               WHERE enabled = 1 AND running = 0 AND next_run_at <= ?
               ORDER BY next_run_at LIMIT ?""", (timestamp, limit),
        ).fetchall()
        result: list[tuple[ScheduledTask, str]] = []
        for row in rows:
            run_id = uuid7()
            next_run = (now + timedelta(seconds=row["interval_seconds"])).isoformat().replace("+00:00", "Z")
            conn.execute(
                """UPDATE scheduled_agent_tasks
                   SET running = 1, last_status = 'running', last_run_at = ?,
                       next_run_at = ?, updated_at = ? WHERE task_id = ? AND running = 0""",
                (timestamp, next_run, timestamp, row["task_id"]),
            )
            conn.execute(
                "INSERT INTO scheduled_agent_task_runs (run_id, task_id, started_at, status) VALUES (?, ?, ?, 'running')",
                (run_id, row["task_id"], timestamp),
            )
            result.append((_task(row), run_id))
    return result


def make_due(task_id: str) -> bool:
    with db(immediate=True) as conn:
        cur = conn.execute(
            "UPDATE scheduled_agent_tasks SET next_run_at = ?, updated_at = ? "
            "WHERE task_id = ? AND running = 0",
            ("1970-01-01T00:00:00Z", now_iso(), task_id),
        )
    return cur.rowcount > 0


def finish(task_id: str, run_id: str, *, status: str, session_id: str | None = None,
           error: str | None = None) -> None:
    timestamp = now_iso()
    with db(immediate=True) as conn:
        row = conn.execute("SELECT failure_count FROM scheduled_agent_tasks WHERE task_id = ?", (task_id,)).fetchone()
        failures = int(row["failure_count"]) if row else 0
        failures = failures + 1 if status == "failed" else 0
        conn.execute(
            """UPDATE scheduled_agent_tasks SET running = 0, last_status = ?, last_error = ?,
               failure_count = ?, updated_at = ? WHERE task_id = ?""",
            (status, error, failures, timestamp, task_id),
        )
        conn.execute(
            """UPDATE scheduled_agent_task_runs SET finished_at = ?, status = ?, session_id = ?, error = ?
               WHERE run_id = ?""",
            (timestamp, status, session_id, error, run_id),
        )


def runs(task_id: str, limit: int = 50) -> list[ScheduledRun]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM scheduled_agent_task_runs WHERE task_id = ? ORDER BY started_at DESC LIMIT ?",
            (task_id, limit),
        ).fetchall()
    return [_run(row) for row in rows]
