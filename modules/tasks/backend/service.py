"""Tasks-Modul — CRUD-Service."""
from __future__ import annotations

import uuid
from typing import Any

from hydrahive.db.connection import db

VALID_STATUSES = {"open", "in_progress", "done", "cancelled"}
VALID_PRIORITIES = {"low", "medium", "high"}


def list_tasks(
    username: str,
    status: str | None = None,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM module_tasks WHERE username = ?"
    params: list[Any] = [username]
    if status:
        sql += " AND status = ?"
        params.append(status)
    if project_id:
        sql += " AND project_id = ?"
        params.append(project_id)
    sql += " ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, created_at ASC"
    with db() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def get_task(username: str, task_id: str) -> dict[str, Any] | None:
    with db() as c:
        row = c.execute(
            "SELECT * FROM module_tasks WHERE id = ? AND username = ?",
            (task_id, username),
        ).fetchone()
        return dict(row) if row else None


def create_task(
    username: str,
    title: str,
    description: str = "",
    priority: str = "medium",
    project_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    task_id = str(uuid.uuid4())
    with db() as c:
        c.execute(
            """
            INSERT INTO module_tasks (id, username, project_id, session_id, title, description, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, username, project_id, session_id, title, description, priority),
        )
    return get_task(username, task_id)  # type: ignore[return-value]


def update_task(
    username: str,
    task_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
) -> dict[str, Any] | None:
    task = get_task(username, task_id)
    if not task:
        return None
    fields: dict[str, Any] = {}
    if title is not None:
        fields["title"] = title
    if description is not None:
        fields["description"] = description
    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Ungültiger Status: {status!r}")
        fields["status"] = status
    if priority is not None:
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"Ungültige Priorität: {priority!r}")
        fields["priority"] = priority
    if not fields:
        return task
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with db() as c:
        c.execute(
            f"UPDATE module_tasks SET {set_clause}, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')"
            " WHERE id = ? AND username = ?",
            [*fields.values(), task_id, username],
        )
    return get_task(username, task_id)


def delete_task(username: str, task_id: str) -> bool:
    with db() as c:
        cur = c.execute(
            "DELETE FROM module_tasks WHERE id = ? AND username = ?",
            (task_id, username),
        )
        return cur.rowcount > 0
