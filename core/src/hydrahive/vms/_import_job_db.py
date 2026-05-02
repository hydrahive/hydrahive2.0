"""DB access for VM import jobs."""
from __future__ import annotations

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


def db_create_job(owner: str, source_path: str, target_qcow2: str,
                  bytes_total: int = 0) -> str:
    job_id = uuid7()
    with db() as conn:
        conn.execute(
            """INSERT INTO vm_import_jobs (job_id, owner, source_path, target_qcow2,
                                            status, bytes_total, created_at)
               VALUES (?, ?, ?, ?, 'queued', ?, ?)""",
            (job_id, owner, source_path, target_qcow2, bytes_total, now_iso()),
        )
    return job_id


def db_update(job_id: str, **fields) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [job_id]
    with db() as conn:
        conn.execute(f"UPDATE vm_import_jobs SET {sets} WHERE job_id = ?", vals)


def db_list(owner: str | None) -> list[dict]:
    with db() as conn:
        if owner is None:
            rows = conn.execute("SELECT * FROM vm_import_jobs ORDER BY created_at DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM vm_import_jobs WHERE owner = ? ORDER BY created_at DESC",
                (owner,),
            ).fetchall()
    return [dict(r) for r in rows]


def db_get(job_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM vm_import_jobs WHERE job_id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def db_delete(job_id: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM vm_import_jobs WHERE job_id = ?", (job_id,))
