"""Transactional orchestration and result projection for remote containers."""

from __future__ import annotations

import json
import sqlite3

from hydrahive.compute import jobs
from hydrahive.compute._job_codec import row_to_job
from hydrahive.compute.models import ComputeJob
from hydrahive.containers import db as cdb
from hydrahive.containers.models import Container
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


class RemoteContainerError(RuntimeError):
    pass


def _container(conn: sqlite3.Connection, container_id: str) -> Container:
    row = conn.execute("SELECT * FROM containers WHERE container_id = ?", (container_id,)).fetchone()
    if row is None:
        raise RemoteContainerError("remote container not found")
    return cdb.row_to_container(row)


def _require_node(conn: sqlite3.Connection, node_id: str, operation: str) -> None:
    row = conn.execute(
        "SELECT kind, status, capabilities_json FROM compute_nodes WHERE node_id = ?",
        (node_id,),
    ).fetchone()
    allowed = {"online"}
    if operation in {"container.stop", "container.delete", "container.inspect"}:
        allowed.add("draining")
    if row is None or row["kind"] != "agent" or row["status"] not in allowed:
        raise RemoteContainerError("remote container node cannot accept this operation")
    try:
        capabilities = json.loads(row["capabilities_json"])
    except (TypeError, ValueError) as exc:
        raise RemoteContainerError("remote node capabilities are invalid") from exc
    instance_types = capabilities.get("instance_types", []) if isinstance(capabilities, dict) else []
    if (
        capabilities.get("incus") is not True
        or not isinstance(instance_types, list)
        or "container" not in instance_types
    ):
        raise RemoteContainerError("remote node does not support containers")


def _insert_job(
    conn: sqlite3.Connection,
    container: Container,
    operation: str,
    payload: dict,
    actor: str,
    *,
    unique: bool = False,
) -> ComputeJob:
    suffix = f"{operation}:{uuid7()}" if unique else operation
    return jobs.create_job(
        node_id=container.node_id,
        resource_kind="container",
        resource_id=container.container_id,
        operation=operation,
        generation=container.generation,
        payload=payload,
        idempotency_key=f"container:{container.container_id}:{container.generation}:{suffix}",
        created_by=actor,
        connection=conn,
    )


def queue_create(container_id: str, *, actor: str) -> ComputeJob:
    try:
        with db(immediate=True) as conn:
            container = _container(conn, container_id)
            _require_node(conn, container.node_id, "container.create")
            if container.actual_state not in {"created", "error"}:
                raise RemoteContainerError("remote container creation is already in progress")
            changed = conn.execute(
                """UPDATE containers SET desired_state = 'running', actual_state = 'starting',
                          generation = generation + 1, last_error_code = NULL,
                          last_error_params = NULL, updated_at = ?
                   WHERE container_id = ? AND generation = ? AND actual_state IN ('created', 'error')""",
                (now_iso(), container_id, container.generation),
            )
            if changed.rowcount != 1:
                raise RemoteContainerError("remote container state changed concurrently")
            current = _container(conn, container_id)
            return _insert_job(
                conn,
                current,
                "container.create",
                {
                    "name": current.name,
                    "image": current.image,
                    "network_mode": current.network_mode,
                    "cpu": current.cpu,
                    "ram_mb": current.ram_mb,
                },
                actor,
            )
    except jobs.JobConflict as exc:
        raise RemoteContainerError("remote container node stopped accepting jobs") from exc


def queue_lifecycle(container_id: str, operation: str, *, actor: str) -> ComputeJob:
    desired, transitional = {
        "container.start": ("running", "starting"),
        "container.stop": ("stopped", "stopping"),
        "container.restart": ("running", "starting"),
        "container.delete": ("deleted", "stopping"),
    }[operation]
    try:
        with db(immediate=True) as conn:
            container = _container(conn, container_id)
            _require_node(conn, container.node_id, operation)
            if container.actual_state in {"starting", "stopping"}:
                raise RemoteContainerError("remote container already has a pending operation")
            changed = conn.execute(
                """UPDATE containers SET desired_state = ?, actual_state = ?, generation = generation + 1,
                          last_error_code = NULL, last_error_params = NULL, updated_at = ?
                   WHERE container_id = ? AND generation = ? AND actual_state NOT IN ('starting', 'stopping')""",
                (desired, transitional, now_iso(), container_id, container.generation),
            )
            if changed.rowcount != 1:
                raise RemoteContainerError("remote container state changed concurrently")
            current = _container(conn, container_id)
            return _insert_job(conn, current, operation, {"name": current.name}, actor)
    except jobs.JobConflict as exc:
        raise RemoteContainerError("remote container node stopped accepting jobs") from exc


def queue_inspect(container_id: str, *, actor: str) -> ComputeJob:
    try:
        with db(immediate=True) as conn:
            container = _container(conn, container_id)
            _require_node(conn, container.node_id, "container.inspect")
            row = conn.execute(
                """SELECT * FROM compute_jobs
                   WHERE node_id = ? AND resource_kind = 'container' AND resource_id = ?
                     AND operation = 'container.inspect' AND generation = ?
                     AND status IN ('queued', 'leased', 'running')
                   ORDER BY created_at DESC LIMIT 1""",
                (container.node_id, container.container_id, container.generation),
            ).fetchone()
            if row is not None:
                return row_to_job(row)
            return _insert_job(
                conn,
                container,
                "container.inspect",
                {"name": container.name},
                actor,
                unique=True,
            )
    except jobs.JobConflict as exc:
        raise RemoteContainerError("remote container node stopped accepting jobs") from exc


from hydrahive.containers._remote_results import (  # noqa: E402
    apply_failure,
    apply_success,
    success_result_is_valid,
)
