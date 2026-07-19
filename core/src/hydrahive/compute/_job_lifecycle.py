"""Lease-checked state transitions for durable compute jobs."""

from __future__ import annotations

import sqlite3

from hydrahive.compute._job_codec import (
    JobConflict,
    JobNotFound,
    dump_job_json,
    row_to_job,
    validate_text,
)
from hydrahive.compute._job_events import append_event
from hydrahive.compute.models import ComputeJob, JSONObject
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "expired"}


def _load(conn: sqlite3.Connection, job_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM compute_jobs WHERE job_id = ?", (job_id,)).fetchone()
    if row is None:
        raise JobNotFound("compute job not found")
    return row


def _lease(row: sqlite3.Row, lease_id: str) -> None:
    if not lease_id or row["lease_id"] != lease_id:
        raise JobConflict("compute job lease does not match")
    if row["lease_until"] is None or row["lease_until"] < now_iso():
        raise JobConflict("compute job lease has expired")


def _updated(conn: sqlite3.Connection, job_id: str) -> ComputeJob:
    return row_to_job(_load(conn, job_id))


def start_job(job_id: str, lease_id: str) -> ComputeJob:
    with db(immediate=True) as conn:
        row = _load(conn, job_id)
        if row["status"] == "running":
            _lease(row, lease_id)
            return row_to_job(row)
        if row["status"] != "leased":
            raise JobConflict("compute job is not leased")
        _lease(row, lease_id)
        timestamp = now_iso()
        conn.execute(
            "UPDATE compute_jobs SET status = 'running', started_at = COALESCE(started_at, ?) WHERE job_id = ?",
            (timestamp, job_id),
        )
        append_event(
            conn,
            job_id=job_id,
            node_id=row["node_id"],
            event_type="running",
            data={},
            actor=f"node:{row['node_id']}",
        )
        return _updated(conn, job_id)


def report_progress(job_id: str, lease_id: str, progress: int, data: JSONObject | None = None) -> ComputeJob:
    if not 0 <= progress <= 99:
        raise ValueError("progress must be between 0 and 99")
    details = data or {}
    dump_job_json(details, "progress data")
    with db(immediate=True) as conn:
        row = _load(conn, job_id)
        if row["status"] != "running":
            raise JobConflict("compute job is not running")
        _lease(row, lease_id)
        if progress < row["progress"]:
            raise JobConflict("compute job progress cannot decrease")
        if progress == row["progress"]:
            return row_to_job(row)
        conn.execute("UPDATE compute_jobs SET progress = ? WHERE job_id = ?", (progress, job_id))
        append_event(
            conn,
            job_id=job_id,
            node_id=row["node_id"],
            event_type="progress",
            data={"progress": progress, "details": details},
            actor=f"node:{row['node_id']}",
        )
        return _updated(conn, job_id)


def _finish(
    job_id: str,
    lease_id: str,
    *,
    target: str,
    event_data: JSONObject,
    error_code: str | None = None,
    error_params: JSONObject | None = None,
) -> ComputeJob:
    with db(immediate=True) as conn:
        row = _load(conn, job_id)
        if row["status"] == target:
            event = conn.execute(
                "SELECT data_json FROM compute_job_events WHERE job_id = ? ORDER BY sequence DESC LIMIT 1",
                (job_id,),
            ).fetchone()
            if event is not None and event["data_json"] == dump_job_json(event_data, "result"):
                return row_to_job(row)
            raise JobConflict("terminal compute job result differs")
        if row["status"] in TERMINAL_STATUSES:
            raise JobConflict("compute job is already terminal")
        if row["status"] not in {"leased", "running"}:
            raise JobConflict("compute job cannot be completed")
        _lease(row, lease_id)
        timestamp = now_iso()
        conn.execute(
            """UPDATE compute_jobs
               SET status = ?, progress = CASE WHEN ? = 'succeeded' THEN 100 ELSE progress END,
                   error_code = ?, error_params_json = ?, finished_at = ?
               WHERE job_id = ?""",
            (
                target,
                target,
                error_code,
                dump_job_json(error_params, "error_params") if error_params is not None else None,
                timestamp,
                job_id,
            ),
        )
        append_event(
            conn,
            job_id=job_id,
            node_id=row["node_id"],
            event_type=target,
            data=event_data,
            actor=f"node:{row['node_id']}",
        )
        return _updated(conn, job_id)


def succeed_job(job_id: str, lease_id: str, result: JSONObject) -> ComputeJob:
    dump_job_json(result, "result")
    return _finish(job_id, lease_id, target="succeeded", event_data={"result": result})


def fail_job(job_id: str, lease_id: str, error_code: str, error_params: JSONObject) -> ComputeJob:
    error_code = validate_text(error_code, "error_code", maximum=128)
    dump_job_json(error_params, "error_params")
    return _finish(
        job_id,
        lease_id,
        target="failed",
        event_data={"error_code": error_code, "error_params": error_params},
        error_code=error_code,
        error_params=error_params,
    )


def cancel_job(job_id: str, *, actor: str) -> ComputeJob:
    actor = validate_text(actor, "actor", maximum=128)
    with db(immediate=True) as conn:
        row = _load(conn, job_id)
        if row["status"] in TERMINAL_STATUSES:
            raise JobConflict("compute job is already terminal")
        if row["status"] == "running":
            raise JobConflict("running compute job cannot be cancelled safely")
        timestamp = now_iso()
        conn.execute(
            """UPDATE compute_jobs
               SET status = 'cancelled', lease_id = NULL, lease_until = NULL, finished_at = ?
               WHERE job_id = ?""",
            (timestamp, job_id),
        )
        append_event(
            conn,
            job_id=job_id,
            node_id=row["node_id"],
            event_type="cancelled",
            data={},
            actor=actor,
        )
        return _updated(conn, job_id)
