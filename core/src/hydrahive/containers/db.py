"""DB-CRUD für Container."""
from __future__ import annotations

import json
import sqlite3

from hydrahive.db.connection import db
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.containers.models import Container


def _row_to_container(r: sqlite3.Row) -> Container:
    params = json.loads(r["last_error_params"]) if r["last_error_params"] else None
    return Container(
        container_id=r["container_id"], owner=r["owner"], name=r["name"],
        description=r["description"], image=r["image"],
        cpu=r["cpu"], ram_mb=r["ram_mb"], network_mode=r["network_mode"],
        desired_state=r["desired_state"], actual_state=r["actual_state"],
        last_error_code=r["last_error_code"], last_error_params=params,
        created_at=r["created_at"], updated_at=r["updated_at"],
    )


def create(owner: str, name: str, image: str, network_mode: str = "bridged",
           cpu: int | None = None, ram_mb: int | None = None,
           description: str | None = None) -> Container:
    cid = uuid7()
    ts = now_iso()
    with db() as conn:
        conn.execute(
            """INSERT INTO containers (container_id, owner, name, description, image,
                                        cpu, ram_mb, network_mode,
                                        desired_state, actual_state, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'stopped', 'created', ?, ?)""",
            (cid, owner, name, description, image, cpu, ram_mb, network_mode, ts, ts),
        )
    return get(cid)  # type: ignore[return-value]


def get(container_id: str) -> Container | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM containers WHERE container_id = ?", (container_id,),
        ).fetchone()
    return _row_to_container(row) if row else None


def list_(owner: str | None = None) -> list[Container]:
    with db() as conn:
        if owner is None:
            rows = conn.execute(
                "SELECT * FROM containers ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM containers WHERE owner = ? ORDER BY created_at DESC",
                (owner,),
            ).fetchall()
    return [_row_to_container(r) for r in rows]


def name_taken(name: str, exclude_id: str | None = None) -> bool:
    with db() as conn:
        if exclude_id:
            row = conn.execute(
                "SELECT 1 FROM containers WHERE name = ? AND container_id != ?",
                (name, exclude_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT 1 FROM containers WHERE name = ?", (name,),
            ).fetchone()
    return row is not None


def update_state(container_id: str, *, desired: str | None = None,
                 actual: str | None = None,
                 error_code: str | None = ..., error_params: dict | None = ...) -> None:
    sets: list[str] = ["updated_at = ?"]
    vals: list = [now_iso()]
    if desired is not None:
        sets.append("desired_state = ?"); vals.append(desired)
    if actual is not None:
        sets.append("actual_state = ?"); vals.append(actual)
    if error_code is not ...:
        sets.append("last_error_code = ?"); vals.append(error_code)
    if error_params is not ...:
        sets.append("last_error_params = ?")
        vals.append(json.dumps(error_params) if error_params else None)
    vals.append(container_id)
    with db() as conn:
        conn.execute(f"UPDATE containers SET {', '.join(sets)} WHERE container_id = ?", vals)


def delete(container_id: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM containers WHERE container_id = ?", (container_id,))
