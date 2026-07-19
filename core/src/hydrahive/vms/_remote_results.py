"""Generation-bound projection of remote VM runtime results."""

from __future__ import annotations

import sqlite3
from contextlib import nullcontext

from hydrahive.compute.models import ComputeJob
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

_EXPECTED = {
    "vm.create_from_image": "running",
    "vm.start": "running",
    "vm.stop": "stopped",
    "vm.restart": "running",
    "vm.delete": "deleted",
}


def success_result_is_valid(job: ComputeJob, result: dict[str, object]) -> bool:
    if job.operation == "vm.inspect":
        return result.get("actual_state") in {"running", "stopped"}
    expected = _EXPECTED.get(job.operation)
    if expected is None or result.get("actual_state") != expected:
        return False
    if job.operation == "vm.create_from_image":
        return result.get("runtime_ref") == job.payload.get("name")
    return True


def apply_success(
    job: ComputeJob,
    result: dict[str, object],
    *,
    connection: sqlite3.Connection | None = None,
) -> None:
    context = nullcontext(connection) if connection is not None else db(immediate=True)
    with context as conn:
        row = conn.execute(
            "SELECT 1 FROM vms WHERE vm_id = ? AND node_id = ? AND generation = ?",
            (job.resource_id, job.node_id, job.generation),
        ).fetchone()
        if row is None:
            return
        expected = _EXPECTED.get(job.operation)
        if job.operation == "vm.inspect":
            expected = result.get("actual_state") if result.get("actual_state") in {"running", "stopped"} else None
        if expected is None or result.get("actual_state") != expected:
            _project_error(conn, job, "agent_result_invalid")
        elif expected == "deleted":
            conn.execute(
                "DELETE FROM vms WHERE vm_id = ? AND node_id = ? AND generation = ?",
                (job.resource_id, job.node_id, job.generation),
            )
        else:
            runtime_ref = result.get("runtime_ref")
            if job.operation == "vm.create_from_image" and isinstance(runtime_ref, str):
                conn.execute(
                    """UPDATE vms SET actual_state = ?, runtime_ref = ?, last_error_code = NULL,
                              last_error_params = NULL, updated_at = ?
                       WHERE vm_id = ? AND node_id = ? AND generation = ?""",
                    (expected, runtime_ref, now_iso(), job.resource_id, job.node_id, job.generation),
                )
            else:
                conn.execute(
                    """UPDATE vms SET actual_state = ?, last_error_code = NULL,
                              last_error_params = NULL, updated_at = ?
                       WHERE vm_id = ? AND node_id = ? AND generation = ?""",
                    (expected, now_iso(), job.resource_id, job.node_id, job.generation),
                )


def _project_error(conn: sqlite3.Connection, job: ComputeJob, error_code: str) -> None:
    conn.execute(
        """UPDATE vms SET actual_state = 'error', last_error_code = ?,
                  last_error_params = NULL, updated_at = ?
           WHERE vm_id = ? AND node_id = ? AND generation = ?""",
        (error_code, now_iso(), job.resource_id, job.node_id, job.generation),
    )


def apply_failure(
    job: ComputeJob,
    error_code: str,
    *,
    connection: sqlite3.Connection | None = None,
) -> None:
    context = nullcontext(connection) if connection is not None else db(immediate=True)
    with context as conn:
        _project_error(conn, job, error_code)
