"""Strict allowlisted Incus-container operations for signed compute jobs."""

from __future__ import annotations

import json

from hydrahive_node._incus_process import run as _run
from hydrahive_node import _incus_state as state
from hydrahive_node._incus_validation import (
    CREATE_FIELDS,
    LIFECYCLE_FIELDS,
    IncusJobError,
    image as _image,
    name as _name,
    optional_int as _optional_int,
)
from hydrahive_node.jobs import VerifiedJob


async def _ownership(name: str, resource_id: str) -> dict | None:
    return await state.ownership(_run, name, resource_id)


async def _checked(*args: str, timeout: float = 60.0) -> str:
    rc, output, _ = await _run(*args, timeout=timeout)
    if rc != 0:
        raise IncusJobError("incus_operation_failed")
    return output


async def _network_matches(name: str, desired: dict[str, str]) -> bool:
    output = await _checked("config", "show", name, "--expanded", "--format=json", timeout=30.0)
    try:
        eth0 = json.loads(output).get("devices", {}).get("eth0", {})
    except (ValueError, AttributeError) as exc:
        raise IncusJobError("incus_inspect_invalid") from exc
    return isinstance(eth0, dict) and all(eth0.get(key) == value for key, value in desired.items())


async def _configure_network(name: str, mode: str) -> None:
    desired = {"type": "none"} if mode == "isolated" else {"type": "nic", "nictype": "bridged", "parent": "br0"}
    if await _network_matches(name, desired):
        return
    settings = [f"{key}={value}" for key, value in desired.items()]
    commands = [
        ("override", *settings),
        ("set", *settings),
        ("add", desired["type"], *settings[1:]),
    ]
    rc = -1
    for action in commands:
        try:
            rc, _, _ = await _run("config", "device", action[0], name, "eth0", *action[1:], timeout=30.0)
        except TimeoutError:
            if await _network_matches(name, desired):
                return
            raise IncusJobError("operation_outcome_unknown") from None
        if rc == 0:
            break
    if rc != 0 or not await _network_matches(name, desired):
        raise IncusJobError("incus_operation_failed")


async def _wait_for_owned_instance(name: str, resource_id: str) -> dict | None:
    return await state.wait_for_owned(_run, name, resource_id)


async def _wait_for_state(name: str, resource_id: str, expected: str | None) -> bool:
    return await state.wait_for_state(_run, name, resource_id, expected)


async def _create(job: VerifiedJob) -> dict[str, object]:
    if set(job.payload) != CREATE_FIELDS or job.resource_id is None:
        raise IncusJobError("container_create_payload_invalid")
    name = _name(job.payload["name"])
    image = _image(job.payload["image"])
    mode = job.payload["network_mode"]
    if mode not in {"bridged", "isolated"}:
        raise IncusJobError("container_network_mode_invalid")
    cpu = _optional_int(job.payload["cpu"], 1, 16, "cpu")
    ram_mb = _optional_int(job.payload["ram_mb"], 64, 32768, "ram")
    instance = await _ownership(name, job.resource_id)
    if instance is None:
        options = ["-c", f"user.hydrahive.id={job.resource_id}"]
        if cpu is not None:
            options += ["-c", f"limits.cpu={cpu}"]
        if ram_mb is not None:
            options += ["-c", f"limits.memory={ram_mb}MiB"]
        timed_out = False
        try:
            rc, _, _ = await _run("init", *options, "--", image, name, timeout=300.0)
        except TimeoutError:
            rc, timed_out = -1, True
        if rc != 0 and await _wait_for_owned_instance(name, job.resource_id) is None:
            raise IncusJobError("operation_outcome_unknown" if timed_out else "incus_operation_failed")
    await _configure_network(name, str(mode))
    instance = await _ownership(name, job.resource_id)
    if instance is None:
        raise IncusJobError("container_not_found")
    if str(instance.get("status", "")).lower() != "running":
        try:
            await _checked("start", name)
        except TimeoutError:
            if not await _wait_for_state(name, job.resource_id, "running"):
                raise IncusJobError("operation_outcome_unknown") from None
    return {"actual_state": "running", "runtime_ref": name}


async def _lifecycle(job: VerifiedJob) -> dict[str, object]:
    if set(job.payload) != LIFECYCLE_FIELDS or job.resource_id is None:
        raise IncusJobError("container_lifecycle_payload_invalid")
    name = _name(job.payload["name"])
    instance = await _ownership(name, job.resource_id)
    if job.operation == "container.delete" and instance is None:
        return {"actual_state": "deleted"}
    if instance is None:
        raise IncusJobError("container_not_found")
    status = str(instance.get("status", "")).lower()
    if job.operation == "container.start":
        if status != "running":
            try:
                await _checked("start", name)
            except TimeoutError:
                if not await _wait_for_state(name, job.resource_id, "running"):
                    raise IncusJobError("operation_outcome_unknown") from None
        return {"actual_state": "running"}
    if job.operation == "container.stop":
        if status != "stopped":
            try:
                await _checked("stop", name, "--force")
            except TimeoutError:
                if not await _wait_for_state(name, job.resource_id, "stopped"):
                    raise IncusJobError("operation_outcome_unknown") from None
        return {"actual_state": "stopped"}
    if job.operation == "container.restart":
        try:
            await _checked("restart", name)
        except TimeoutError as exc:
            raise IncusJobError("operation_outcome_unknown") from exc
        return {"actual_state": "running"}
    if job.operation == "container.delete":
        try:
            await _checked("delete", name, "--force")
        except TimeoutError:
            if not await _wait_for_state(name, job.resource_id, None):
                raise IncusJobError("operation_outcome_unknown") from None
        return {"actual_state": "deleted"}
    if status not in {"running", "stopped"}:
        raise IncusJobError("container_state_unknown")
    return {"actual_state": status}


async def execute(job: VerifiedJob) -> dict[str, object]:
    if job.resource_kind == "vm":
        from hydrahive_node import _incus_vm

        return await _incus_vm.execute(job)
    if job.resource_kind != "container" or not job.operation.startswith("container."):
        raise IncusJobError("container_operation_invalid")
    if job.operation == "container.create":
        return await _create(job)
    if job.operation not in {
        "container.start",
        "container.stop",
        "container.restart",
        "container.delete",
        "container.inspect",
    }:
        raise IncusJobError("container_operation_invalid")
    return await _lifecycle(job)
