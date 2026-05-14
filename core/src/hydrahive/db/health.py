from __future__ import annotations

import json
from typing import Any

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


def insert(
    payload: dict,
    automation_name: str | None = None,
    automation_id: str | None = None,
    session_id: str | None = None,
    period: str | None = None,
    aggregation: str | None = None,
) -> str:
    record_id = uuid7()
    with db() as conn:
        conn.execute(
            """INSERT INTO health_ingest
               (id, received_at, automation_name, automation_id, session_id, period, aggregation, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (record_id, now_iso(), automation_name, automation_id,
             session_id, period, aggregation, json.dumps(payload)),
        )
    return record_id


def list_recent(limit: int = 50, automation_id: str | None = None) -> list[dict]:
    with db() as conn:
        if automation_id:
            rows = conn.execute(
                """SELECT id, received_at, automation_name, automation_id, session_id,
                          period, aggregation
                   FROM health_ingest WHERE automation_id = ?
                   ORDER BY received_at DESC LIMIT ?""",
                (automation_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, received_at, automation_name, automation_id, session_id,
                          period, aggregation
                   FROM health_ingest ORDER BY received_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def get_payload(record_id: str) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute(
            "SELECT payload FROM health_ingest WHERE id = ?", (record_id,)
        ).fetchone()
    if not row:
        return None
    return json.loads(row["payload"])
