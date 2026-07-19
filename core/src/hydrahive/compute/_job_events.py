"""Append-only event and audit writes for compute-job transitions."""

from __future__ import annotations

import sqlite3

from hydrahive.compute import audit
from hydrahive.compute._job_codec import dump_job_json
from hydrahive.compute.models import JSONObject
from hydrahive.db._utils import now_iso


def append_event(
    conn: sqlite3.Connection,
    *,
    job_id: str,
    node_id: str,
    event_type: str,
    data: JSONObject,
    actor: str,
) -> None:
    sequence = conn.execute(
        "SELECT COALESCE(MAX(sequence), -1) + 1 FROM compute_job_events WHERE job_id = ?",
        (job_id,),
    ).fetchone()[0]
    conn.execute(
        """INSERT INTO compute_job_events
               (job_id, sequence, event_type, data_json, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (job_id, sequence, event_type, dump_job_json(data, "job event"), now_iso()),
    )
    audit.record_in_connection(
        conn,
        actor=actor,
        action=f"job.{event_type}",
        node_id=node_id,
        details={"job_id": job_id, "sequence": sequence},
    )
