"""DB-Zugriff für SMB-Mounts — Mapping zu/von Dataclass + simple CRUD.

Spiegelt das Muster aus vms/db.py (set_project / list_for_project /
clear_project_assignments für die Projekt-Zuweisung).
"""
from __future__ import annotations

import sqlite3

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db
from hydrahive.smbmounts.models import SmbMount

__all__ = [
    "create_mount", "get_mount", "list_mounts", "delete_mount",
    "update_mount", "set_state", "set_project",
    "list_for_project", "clear_project_assignments", "name_taken",
]


def _row_to_mount(r: sqlite3.Row) -> SmbMount:
    return SmbMount(
        mount_id=r["mount_id"], owner=r["owner"], name=r["name"],
        host=r["host"], share=r["share"], subpath=r["subpath"],
        credential=r["credential"], read_only=bool(r["read_only"]),
        options=r["options"], project_id=r["project_id"],
        mount_state=r["mount_state"], last_error_code=r["last_error_code"],
        created_at=r["created_at"], updated_at=r["updated_at"],
    )


def create_mount(owner: str, name: str, host: str, share: str,
                 subpath: str | None = None, credential: str | None = None,
                 read_only: bool = False, options: str | None = None) -> SmbMount:
    mount_id = uuid7()
    ts = now_iso()
    with db() as conn:
        conn.execute(
            """INSERT INTO smb_mounts
                   (mount_id, owner, name, host, share, subpath, credential,
                    read_only, options, mount_state, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'unmounted', ?, ?)""",
            (mount_id, owner, name, host, share, subpath, credential,
             1 if read_only else 0, options, ts, ts),
        )
    return get_mount(mount_id)  # type: ignore[return-value]


def get_mount(mount_id: str) -> SmbMount | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM smb_mounts WHERE mount_id = ?", (mount_id,)
        ).fetchone()
    return _row_to_mount(row) if row else None


def list_mounts(owner: str | None = None) -> list[SmbMount]:
    with db() as conn:
        if owner is None:
            rows = conn.execute(
                "SELECT * FROM smb_mounts ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM smb_mounts WHERE owner = ? ORDER BY created_at DESC",
                (owner,),
            ).fetchall()
    return [_row_to_mount(r) for r in rows]


def delete_mount(mount_id: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM smb_mounts WHERE mount_id = ?", (mount_id,))


def update_mount(mount_id: str, *, host: str | None = None,
                 share: str | None = None, subpath: str | None = None,
                 credential: str | None = None, read_only: bool | None = None,
                 options: str | None = None) -> None:
    fields: list[str] = []
    values: list[object] = []
    for col, val in (
        ("host", host), ("share", share), ("subpath", subpath),
        ("credential", credential), ("options", options),
    ):
        if val is not None:
            fields.append(f"{col} = ?")
            values.append(val)
    if read_only is not None:
        fields.append("read_only = ?")
        values.append(1 if read_only else 0)
    if not fields:
        return
    fields.append("updated_at = ?")
    values.append(now_iso())
    values.append(mount_id)
    with db() as conn:
        conn.execute(
            f"UPDATE smb_mounts SET {', '.join(fields)} WHERE mount_id = ?",
            values,
        )


def set_state(mount_id: str, state: str, error_code: str | None = None) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE smb_mounts SET mount_state = ?, last_error_code = ?, "
            "updated_at = ? WHERE mount_id = ?",
            (state, error_code, now_iso(), mount_id),
        )


def set_project(mount_id: str, project_id: str | None) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE smb_mounts SET project_id = ?, updated_at = ? WHERE mount_id = ?",
            (project_id, now_iso(), mount_id),
        )


def list_for_project(project_id: str) -> list[SmbMount]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM smb_mounts WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    return [_row_to_mount(r) for r in rows]


def clear_project_assignments(project_id: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE smb_mounts SET project_id = NULL WHERE project_id = ?",
            (project_id,),
        )


def name_taken(owner: str, name: str, exclude_id: str | None = None) -> bool:
    with db() as conn:
        if exclude_id:
            row = conn.execute(
                "SELECT 1 FROM smb_mounts WHERE owner = ? AND name = ? "
                "AND mount_id != ?",
                (owner, name, exclude_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT 1 FROM smb_mounts WHERE owner = ? AND name = ?",
                (owner, name),
            ).fetchone()
    return row is not None
