"""Gruppen, Mitglieder und Audit (Spec access-groups §6).

Alle Nutzer-Verweise über die stabile user_id. Jede Änderung schreibt genau
einen Audit-Eintrag in derselben Transaktion.
"""
from __future__ import annotations

import sqlite3

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


class GroupExists(ValueError):
    """Eine Gruppe mit diesem Namen gibt es schon."""


class GroupNotFound(LookupError):
    """Die Gruppe gibt es nicht."""


def audit(conn: sqlite3.Connection, actor_id: str, action: str, target: str, detail: str = "") -> None:
    conn.execute(
        "INSERT INTO access_audit (at, actor_id, action, target, detail) VALUES (?, ?, ?, ?, ?)",
        (now_iso(), actor_id, action, target, detail),
    )


def audit_for(target: str) -> list[dict]:
    with db() as c:
        rows = c.execute(
            "SELECT at, actor_id, action, target, detail FROM access_audit "
            "WHERE target = ? ORDER BY id",
            (target,),
        ).fetchall()
    return [dict(r) for r in rows]


def create_group(name: str, description: str, *, actor_id: str) -> dict:
    gid, now = uuid7(), now_iso()
    try:
        with db() as c:
            c.execute(
                "INSERT INTO access_groups (id, name, description, created_by, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (gid, name, description, actor_id, now, now),
            )
            audit(c, actor_id, "group_create", f"group:{gid}", name)
    except sqlite3.IntegrityError as exc:
        raise GroupExists(name) from exc
    return get_group(gid)  # type: ignore[return-value]


def get_group(group_id: str) -> dict | None:
    with db() as c:
        row = c.execute(
            "SELECT id, name, description, created_by, created_at, updated_at "
            "FROM access_groups WHERE id = ?",
            (group_id,),
        ).fetchone()
    return dict(row) if row else None


def list_groups() -> list[dict]:
    with db() as c:
        rows = c.execute(
            "SELECT g.id, g.name, g.description, g.created_at, g.updated_at, "
            "(SELECT COUNT(*) FROM access_group_members m WHERE m.group_id = g.id) AS member_count "
            "FROM access_groups g ORDER BY g.name COLLATE NOCASE"
        ).fetchall()
    return [dict(r) for r in rows]


def update_group(group_id: str, *, name: str | None = None, description: str | None = None,
                 actor_id: str) -> dict:
    if get_group(group_id) is None:
        raise GroupNotFound(group_id)
    try:
        with db() as c:
            if name is not None:
                c.execute("UPDATE access_groups SET name = ?, updated_at = ? WHERE id = ?",
                          (name, now_iso(), group_id))
            if description is not None:
                c.execute("UPDATE access_groups SET description = ?, updated_at = ? WHERE id = ?",
                          (description, now_iso(), group_id))
            audit(c, actor_id, "group_update", f"group:{group_id}", name or "")
    except sqlite3.IntegrityError as exc:
        raise GroupExists(name or "") from exc
    return get_group(group_id)  # type: ignore[return-value]


def delete_group(group_id: str, *, actor_id: str) -> None:
    with db() as c:
        n = c.execute("DELETE FROM access_groups WHERE id = ?", (group_id,)).rowcount
        if n == 0:
            raise GroupNotFound(group_id)
        # Freigaben an die Gruppe verlieren ihren Sinn.
        from hydrahive.access.grants import purge_subject
        purge_subject(c, "group", group_id)
        audit(c, actor_id, "group_delete", f"group:{group_id}")


def add_member(group_id: str, user_id: str, *, actor_id: str) -> None:
    if get_group(group_id) is None:
        raise GroupNotFound(group_id)
    with db() as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO access_group_members (group_id, user_id, added_by, added_at) "
            "VALUES (?, ?, ?, ?)",
            (group_id, user_id, actor_id, now_iso()),
        )
        if cur.rowcount:
            audit(c, actor_id, "group_add_member", f"group:{group_id}", user_id)


def remove_member(group_id: str, user_id: str, *, actor_id: str) -> None:
    with db() as c:
        cur = c.execute("DELETE FROM access_group_members WHERE group_id = ? AND user_id = ?",
                        (group_id, user_id))
        if cur.rowcount:
            audit(c, actor_id, "group_remove_member", f"group:{group_id}", user_id)


def members_of(group_id: str) -> list[str]:
    with db() as c:
        rows = c.execute(
            "SELECT user_id FROM access_group_members WHERE group_id = ? ORDER BY added_at, user_id",
            (group_id,),
        ).fetchall()
    return [r[0] for r in rows]


def groups_of(user_id: str) -> list[str]:
    with db() as c:
        rows = c.execute("SELECT group_id FROM access_group_members WHERE user_id = ?",
                         (user_id,)).fetchall()
    return [r[0] for r in rows]
