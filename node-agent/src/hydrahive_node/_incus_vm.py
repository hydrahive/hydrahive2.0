"""Strict allowlisted Incus virtual-machine operations for signed compute jobs.

VMs reuse the container adapter's ownership, network and state helpers but add a
``--vm`` launch with an explicit root-disk size and a hard KVM-capability gate.
ISO boot, image import, host paths and device passthrough are intentionally not
reachable through this adapter.
"""

from __future__ import annotations

import os
from pathlib import Path

from hydrahive_node import _incus_state as state
from hydrahive_node._incus_validation import (
    IncusJobError,
    image as _image,
    name as _name,
    optional_int as _optional_int,
)
from hydrahive_node.jobs import VerifiedJob

VM_CREATE_FIELDS = {"name", "image", "network_mode", "cpu", "ram_mb", "disk_gb"}
VM_LIFECYCLE_FIELDS = {"name"}
KVM_DEVICE = Path("/dev/kvm")


async def _run(*args: str, timeout: float = 60.0) -> tuple[int, str, str]:
    # Delegate to the container adapter's runner so a single subprocess seam is
    # shared (and test monkeypatches of incus._run intercept VM calls too).
    from hydrahive_node import incus

    return await incus._run(*args, timeout=timeout)


def _kvm_available() -> bool:
    return KVM_DEVICE.exists() and os.access(KVM_DEVICE, os.R_OK | os.W_OK)


def _required_int(value: object, minimum: int, maximum: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise IncusJobError(f"vm_{field}_invalid")
    return value


async def _ownership(name: str, resource_id: str) -> dict | None:
    return await state.ownership(_run, name, resource_id)


async def _checked(*args: str, timeout: float = 60.0) -> str:
    rc, output, _ = await _run(*args, timeout=timeout)
    if rc != 0:
        raise IncusJobError("incus_operation_failed")
    return output


async def _wait_for_owned_instance(name: str, resource_id: str) -> dict | None:
    return await state.wait_for_owned(_run, name, resource_id)


async def _wait_for_state(name: str, resource_id: str, expected: str | None) -> bool:
    return await state.wait_for_state(_run, name, resource_id, expected)


async def _create(job: VerifiedJob) -> dict[str, object]:
    if set(job.payload) != VM_CREATE_FIELDS or job.resource_id is None:
        raise IncusJobError("vm_create_payload_invalid")
    if not _kvm_available():
        raise IncusJobError("vm_kvm_unavailable")
    name = _name(job.payload["name"])
    image = _image(job.payload["image"])
    mode = job.payload["network_mode"]
    if mode not in {"bridged", "isolated"}:
        raise IncusJobError("container_network_mode_invalid")
    cpu = _optional_int(job.payload["cpu"], 1, 64, "cpu")
    ram_mb = _optional_int(job.payload["ram_mb"], 256, 262144, "ram")
    disk_gb = _required_int(job.payload["disk_gb"], 1, 2048, "disk")

    instance = await _ownership(name, job.resource_id)
    if instance is None:
        options = [
            "--vm",
            "-c", f"user.hydrahive.id={job.resource_id}",
            "-d", f"root,size={disk_gb}GiB",
        ]
        if cpu is not None:
            options += ["-c", f"limits.cpu={cpu}"]
        if ram_mb is not None:
            options += ["-c", f"limits.memory={ram_mb}MiB"]
        timed_out = False
        try:
            rc, _, _ = await _run("init", *options, "--", image, name, timeout=600.0)
        except TimeoutError:
            rc, timed_out = -1, True
        if rc != 0 and await _wait_for_owned_instance(name, job.resource_id) is None:
            raise IncusJobError("operation_outcome_unknown" if timed_out else "incus_operation_failed")

    # Reuse the container network reconciliation (bridged -> br0, isolated -> none).
    from hydrahive_node.incus import _configure_network

    await _configure_network(name, str(mode))
    instance = await _ownership(name, job.resource_id)
    if instance is None:
        raise IncusJobError("vm_not_found")
    if str(instance.get("status", "")).lower() != "running":
        try:
            await _checked("start", name)
        except TimeoutError:
            if not await _wait_for_state(name, job.resource_id, "running"):
                raise IncusJobError("operation_outcome_unknown") from None
    return {"actual_state": "running", "runtime_ref": name}


async def _lifecycle(job: VerifiedJob) -> dict[str, object]:
    if set(job.payload) != VM_LIFECYCLE_FIELDS or job.resource_id is None:
        raise IncusJobError("vm_lifecycle_payload_invalid")
    name = _name(job.payload["name"])
    instance = await _ownership(name, job.resource_id)
    if job.operation == "vm.delete" and instance is None:
        return {"actual_state": "deleted"}
    if instance is None:
        raise IncusJobError("vm_not_found")
    status = str(instance.get("status", "")).lower()
    if job.operation == "vm.start":
        if status != "running":
            try:
                await _checked("start", name)
            except TimeoutError:
                if not await _wait_for_state(name, job.resource_id, "running"):
                    raise IncusJobError("operation_outcome_unknown") from None
        return {"actual_state": "running"}
    if job.operation == "vm.stop":
        if status != "stopped":
            try:
                await _checked("stop", name, "--force")
            except TimeoutError:
                if not await _wait_for_state(name, job.resource_id, "stopped"):
                    raise IncusJobError("operation_outcome_unknown") from None
        return {"actual_state": "stopped"}
    if job.operation == "vm.restart":
        try:
            await _checked("restart", name)
        except TimeoutError as exc:
            raise IncusJobError("operation_outcome_unknown") from exc
        return {"actual_state": "running"}
    if job.operation == "vm.delete":
        try:
            await _checked("delete", name, "--force")
        except TimeoutError:
            if not await _wait_for_state(name, job.resource_id, None):
                raise IncusJobError("operation_outcome_unknown") from None
        return {"actual_state": "deleted"}
    if status not in {"running", "stopped"}:
        raise IncusJobError("vm_state_unknown")
    return {"actual_state": status}


async def execute(job: VerifiedJob) -> dict[str, object]:
    if job.resource_kind != "vm" or not job.operation.startswith("vm."):
        raise IncusJobError("vm_operation_invalid")
    if job.operation == "vm.create_from_image":
        return await _create(job)
    if job.operation not in {"vm.start", "vm.stop", "vm.restart", "vm.delete", "vm.inspect"}:
        raise IncusJobError("vm_operation_invalid")
    return await _lifecycle(job)
