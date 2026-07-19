from __future__ import annotations

import asyncio
import json

import pytest

from hydrahive_node import incus
from hydrahive_node import _incus_vm
from hydrahive_node.jobs import VerifiedJob

RESOURCE_ID = "019f7be0-95fb-73d3-a87a-2290c85ea427"


def _job(operation: str, payload: dict[str, object], *, resource_id: str = RESOURCE_ID) -> VerifiedJob:
    return VerifiedJob(
        job_id="job-id",
        node_id="node-one",
        resource_kind="vm",
        resource_id=resource_id,
        operation=operation,
        generation=1,
        payload=payload,
        idempotency_key=f"{operation}:1",
        lease_id="lease-id",
        lease_until="2099-01-01T00:00:00Z",
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "--project=evil", "image": "images:debian/12", "network_mode": "bridged", "cpu": 2, "ram_mb": 2048, "disk_gb": 10},
        {"name": "demo", "image": "--target=evil", "network_mode": "bridged", "cpu": 2, "ram_mb": 2048, "disk_gb": 10},
        {"name": "demo", "image": "images:debian/12", "network_mode": "host", "cpu": 2, "ram_mb": 2048, "disk_gb": 10},
        # unknown extra field (e.g. iso / passthrough smuggled in) must be rejected before any subprocess
        {"name": "demo", "image": "images:debian/12", "network_mode": "bridged", "cpu": 2, "ram_mb": 2048, "disk_gb": 10, "iso": "evil.iso"},
        # missing disk
        {"name": "demo", "image": "images:debian/12", "network_mode": "bridged", "cpu": 2, "ram_mb": 2048},
    ],
)
def test_vm_create_rejects_unsafe_or_unknown_payload_before_subprocess(monkeypatch, payload) -> None:
    async def forbidden(*args, **kwargs):
        pytest.fail("invalid payload reached incus subprocess")

    monkeypatch.setattr(incus, "_run", forbidden)
    monkeypatch.setattr(_incus_vm, "_kvm_available", lambda: True)
    with pytest.raises(incus.IncusJobError):
        asyncio.run(incus.execute(_job("vm.create_from_image", payload)))


def test_vm_create_requires_kvm_capability(monkeypatch) -> None:
    async def forbidden(*args, **kwargs):
        pytest.fail("VM create reached subprocess without KVM")

    monkeypatch.setattr(incus, "_run", forbidden)
    monkeypatch.setattr(_incus_vm, "_kvm_available", lambda: False)
    with pytest.raises(incus.IncusJobError, match="kvm"):
        asyncio.run(incus.execute(_job("vm.create_from_image", {
            "name": "demo", "image": "images:debian/12", "network_mode": "bridged",
            "cpu": 2, "ram_mb": 2048, "disk_gb": 10,
        })))


def test_vm_create_uses_vm_flag_fixed_argv_and_starts(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []
    status: str | None = None
    network: dict[str, str] = {}

    async def fake_run(*args: str, timeout: float = 60.0):
        nonlocal status
        calls.append(args)
        if args[0] == "list":
            instances = [{"name": "demo", "status": status, "type": "virtual-machine"}] if status is not None else []
            return (0, json.dumps(instances), "")
        if args[:2] == ("config", "get"):
            return (0, f"{RESOURCE_ID}\n", "")
        if args[:3] == ("config", "device", "override"):
            network.update(item.split("=", 1) for item in args[5:])
        if args[:2] == ("config", "show"):
            return (0, json.dumps({"devices": {"eth0": network}}), "")
        if args[0] == "init":
            status = "Stopped"
        elif args[0] == "start":
            status = "Running"
        return (0, "", "")

    monkeypatch.setattr(incus, "_run", fake_run)
    monkeypatch.setattr(_incus_vm, "_kvm_available", lambda: True)
    result = asyncio.run(incus.execute(_job("vm.create_from_image", {
        "name": "demo", "image": "images:debian/12", "network_mode": "bridged",
        "cpu": 2, "ram_mb": 2048, "disk_gb": 10,
    })))

    launch = next(call for call in calls if call[0] == "init")
    assert "--vm" in launch
    assert launch[-3:] == ("--", "images:debian/12", "demo")
    assert "user.hydrahive.id=019f7be0-95fb-73d3-a87a-2290c85ea427" in launch
    assert any(arg.startswith("root,size=") for arg in launch)
    assert "limits.cpu=2" in launch
    assert "limits.memory=2048MiB" in launch
    # init before network before start
    assert next(i for i, c in enumerate(calls) if c[0] == "init") < next(
        i for i, c in enumerate(calls) if c[0] == "start"
    )
    assert result == {"actual_state": "running", "runtime_ref": "demo"}


def test_vm_create_is_idempotent_for_owned_instance(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []
    network: dict[str, str] = {"type": "nic", "nictype": "bridged", "parent": "br0"}

    async def existing(*args: str, timeout: float = 60.0):
        calls.append(args)
        if args[0] == "list":
            return (0, json.dumps([{"name": "demo", "status": "Running", "type": "virtual-machine"}]), "")
        if args[:2] == ("config", "get"):
            return (0, f"{RESOURCE_ID}\n", "")
        if args[:2] == ("config", "show"):
            return (0, json.dumps({"devices": {"eth0": network}}), "")
        return (0, "", "")

    monkeypatch.setattr(incus, "_run", existing)
    monkeypatch.setattr(_incus_vm, "_kvm_available", lambda: True)
    asyncio.run(incus.execute(_job("vm.create_from_image", {
        "name": "demo", "image": "images:debian/12", "network_mode": "bridged",
        "cpu": 2, "ram_mb": 2048, "disk_gb": 10,
    })))
    assert not any(call[0] == "init" for call in calls)


def test_vm_lifecycle_requires_matching_ownership(monkeypatch) -> None:
    async def foreign(*args: str, timeout: float = 60.0):
        if args[0] == "list":
            return (0, json.dumps([{"name": "demo", "status": "Running", "type": "virtual-machine"}]), "")
        if args[:2] == ("config", "get"):
            return (0, "different-owner\n", "")
        return (0, "", "")

    monkeypatch.setattr(incus, "_run", foreign)
    with pytest.raises(incus.IncusJobError, match="ownership"):
        asyncio.run(incus.execute(_job("vm.delete", {"name": "demo"})))


def test_vm_lifecycle_stop_start_delete(monkeypatch) -> None:
    def make_runner(initial_status: str):
        state = {"status": initial_status}

        async def run(*args: str, timeout: float = 60.0):
            if args[0] == "list":
                if state["status"] == "absent":
                    return (0, json.dumps([]), "")
                return (0, json.dumps([{"name": "demo", "status": state["status"], "type": "virtual-machine"}]), "")
            if args[:2] == ("config", "get"):
                return (0, f"{RESOURCE_ID}\n", "")
            if args[0] == "stop":
                state["status"] = "Stopped"
            elif args[0] == "start":
                state["status"] = "Running"
            elif args[0] == "delete":
                state["status"] = "absent"
            return (0, "", "")

        return run

    monkeypatch.setattr(incus, "_run", make_runner("Running"))
    assert asyncio.run(incus.execute(_job("vm.stop", {"name": "demo"}))) == {"actual_state": "stopped"}

    monkeypatch.setattr(incus, "_run", make_runner("Stopped"))
    assert asyncio.run(incus.execute(_job("vm.start", {"name": "demo"}))) == {"actual_state": "running"}

    monkeypatch.setattr(incus, "_run", make_runner("Stopped"))
    assert asyncio.run(incus.execute(_job("vm.delete", {"name": "demo"}))) == {"actual_state": "deleted"}


def test_vm_inspect_returns_state(monkeypatch) -> None:
    async def run(*args: str, timeout: float = 60.0):
        if args[0] == "list":
            return (0, json.dumps([{"name": "demo", "status": "Running", "type": "virtual-machine"}]), "")
        if args[:2] == ("config", "get"):
            return (0, f"{RESOURCE_ID}\n", "")
        return (0, "", "")

    monkeypatch.setattr(incus, "_run", run)
    assert asyncio.run(incus.execute(_job("vm.inspect", {"name": "demo"}))) == {"actual_state": "running"}


def test_vm_delete_absent_is_success(monkeypatch) -> None:
    async def run(*args: str, timeout: float = 60.0):
        if args[0] == "list":
            return (0, json.dumps([]), "")
        return (0, "", "")

    monkeypatch.setattr(incus, "_run", run)
    assert asyncio.run(incus.execute(_job("vm.delete", {"name": "demo"}))) == {"actual_state": "deleted"}
