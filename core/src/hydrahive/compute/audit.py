"""Append-only audit records for compute security operations."""

from __future__ import annotations

import json
import sqlite3

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

MAX_AUDIT_JSON_BYTES = 16 * 1024


def record_in_connection(
    conn: sqlite3.Connection,
    *,
    actor: str,
    action: str,
    node_id: str | None = None,
    details: dict | None = None,
) -> None:
    details_json = None
    if details is not None:
        details_json = json.dumps(
            details,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        )
        if len(details_json.encode("utf-8")) > MAX_AUDIT_JSON_BYTES:
            raise ValueError("compute audit details are too large")
    conn.execute(
        """INSERT INTO compute_audit_log
               (audit_id, actor, action, node_id, details_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (uuid7(), actor, action, node_id, details_json, now_iso()),
    )


def record(
    *,
    actor: str,
    action: str,
    node_id: str | None = None,
    details: dict | None = None,
) -> None:
    with db() as conn:
        record_in_connection(
            conn,
            actor=actor,
            action=action,
            node_id=node_id,
            details=details,
        )


def list_records(*, node_id: str | None = None, limit: int = 200) -> list[dict]:
    limit = max(1, min(limit, 500))
    with db() as conn:
        if node_id is None:
            rows = conn.execute(
                "SELECT * FROM compute_audit_log ORDER BY created_at DESC, audit_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM compute_audit_log WHERE node_id = ?
                   ORDER BY created_at DESC, audit_id DESC LIMIT ?""",
                (node_id, limit),
            ).fetchall()
    return [
        {
            "audit_id": row["audit_id"],
            "actor": row["actor"],
            "action": row["action"],
            "node_id": row["node_id"],
            "details": json.loads(row["details_json"]) if row["details_json"] else None,
            "created_at": row["created_at"],
        }
        for row in rows
    ]
