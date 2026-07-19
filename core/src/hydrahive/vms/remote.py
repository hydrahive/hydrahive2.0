"""Transactional orchestration and result projection for remote image VMs.

Mirrors ``containers.remote`` but targets image-based Incus VMs on agent nodes.
Local QEMU VMs keep their existing lifecycle; this module never touches them.
"""

from __future__ import annotations

import json
import sqlite3

from hydrahive.compute import jobs
from hydrahive.compute._job_codec import row_to_job
from hydrahive.compute.models import ComputeJob
from hydrahive.vms import db as vmdb
from hydrahive.vms.models import VM
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


class RemoteVMError(RuntimeError):
    pass


def _vm(conn: sqlite3.Connection, vm_id: str) -> VM:
    row = conn.execute("SELECT * FROM vms WHERE vm_id = ?", (vm_id,)).fetchone()
    if row is None:
        raise RemoteVMError("remote vm not found")
    return vmdb._row_to_vm(row)


def _require_node(conn: sqlite3.Connection, node_id: str, operation: str) -> None:
    row = conn.execute(
        "SELECT kind, status, capabilities_json FROM compute_nodes WHERE node_id = ?",
        (node_id,),
    ).fetchone()
    allowed = {"online"}
    if operation in {"vm.stop", "vm.delete", "vm.inspect"}:
        allowed.add("draining")
    if row is None or row["kind"] != "agent" or row["status"] not in allowed:
        raise RemoteVMError("remote vm node cannot accept this operation")
    try:
        capabilities = json.loads(row["capabilities_json"])
    except (TypeError, ValueError) as exc:
        raise RemoteVMError("remote node capabilities are invalid") from exc
    instance_types = capabilities.get("instance_types", []) if isinstance(capabilities, dict) else []
    if (
        not isinstance(capabilities, dict)
        or capabilities.get("incus") is not True
        or capabilities.get("kvm") is not True
        or not isinstance(instance_types, list)
        or "vm" not in instance_types
    ):
        raise RemoteVMError("remote node does not support virtual machines")


def _insert_job(
    conn: sqlite3.Connection,
    vm: VM,
    operation: str,
    payload: dict,
    actor: str,
    *,
    unique: bool = False,
) -> ComputeJob:
    suffix = f"{operation}:{uuid7()}" if unique else operation
    return jobs.create_job(
        node_id=vm.node_id,
        resource_kind="vm",
        resource_id=vm.vm_id,
        operation=operation,
        generation=vm.generation,
        payload=payload,
        idempotency_key=f"vm:{vm.vm_id}:{vm.generation}:{suffix}",
        created_by=actor,
        connection=conn,
    )


def queue_create(vm_id: str, *, actor: str) -> ComputeJob:
    try:
        with db(immediate=True) as conn:
            vm = _vm(conn, vm_id)
            _require_node(conn, vm.node_id, "vm.create_from_image")
            if vm.image is None:
                raise RemoteVMError("remote vm has no source image")
            if vm.actual_state not in {"created", "error"}:
                raise RemoteVMError("remote vm creation is already in progress")
            changed = conn.execute(
                """UPDATE vms SET desired_state = 'running', actual_state = 'starting',
                          generation = generation + 1, last_error_code = NULL,
                          last_error_params = NULL, updated_at = ?
                   WHERE vm_id = ? AND generation = ? AND actual_state IN ('created', 'error')""",
                (now_iso(), vm_id, vm.generation),
            )
            if changed.rowcount != 1:
                raise RemoteVMError("remote vm state changed concurrently")
            current = _vm(conn, vm_id)
            return _insert_job(
                conn,
                current,
                "vm.create_from_image",
                {
                    "name": current.name,
                    "image": current.image,
                    "cpu": current.cpu,
                    "ram_mb": current.ram_mb,
                    "disk_gb": current.disk_gb,
                    "network_mode": current.network_mode,
                },
                actor,
            )
    except jobs.JobConflict as exc:
        raise RemoteVMError("remote vm node stopped accepting jobs") from exc


def queue_lifecycle(vm_id: str, operation: str, *, actor: str) -> ComputeJob:
    desired, transitional = {
        "vm.start": ("running", "starting"),
        "vm.stop": ("stopped", "stopping"),
        "vm.restart": ("running", "starting"),
        "vm.delete": ("stopped", "stopping"),
    }[operation]
    try:
        with db(immediate=True) as conn:
            vm = _vm(conn, vm_id)
            _require_node(conn, vm.node_id, operation)
            if vm.actual_state in {"starting", "stopping"}:
                raise RemoteVMError("remote vm already has a pending operation")
            changed = conn.execute(
                """UPDATE vms SET desired_state = ?, actual_state = ?, generation = generation + 1,
                          last_error_code = NULL, last_error_params = NULL, updated_at = ?
                   WHERE vm_id = ? AND generation = ? AND actual_state NOT IN ('starting', 'stopping')""",
                (desired, transitional, now_iso(), vm_id, vm.generation),
            )
            if changed.rowcount != 1:
                raise RemoteVMError("remote vm state changed concurrently")
            current = _vm(conn, vm_id)
            return _insert_job(conn, current, operation, {"name": current.name}, actor)
    except jobs.JobConflict as exc:
        raise RemoteVMError("remote vm node stopped accepting jobs") from exc


def queue_inspect(vm_id: str, *, actor: str) -> ComputeJob:
    try:
        with db(immediate=True) as conn:
            vm = _vm(conn, vm_id)
            _require_node(conn, vm.node_id, "vm.inspect")
            row = conn.execute(
                """SELECT * FROM compute_jobs
                   WHERE node_id = ? AND resource_kind = 'vm' AND resource_id = ?
                     AND operation = 'vm.inspect' AND generation = ?
                     AND status IN ('queued', 'leased', 'running')
                   ORDER BY created_at DESC LIMIT 1""",
                (vm.node_id, vm.vm_id, vm.generation),
            ).fetchone()
            if row is not None:
                return row_to_job(row)
            return _insert_job(conn, vm, "vm.inspect", {"name": vm.name}, actor, unique=True)
    except jobs.JobConflict as exc:
        raise RemoteVMError("remote vm node stopped accepting jobs") from exc


from hydrahive.vms._remote_results import (  # noqa: E402
    apply_failure,
    apply_success,
    success_result_is_valid,
)
