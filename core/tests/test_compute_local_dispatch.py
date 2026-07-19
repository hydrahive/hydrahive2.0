from __future__ import annotations

import asyncio

import pytest

from hydrahive.containers import lifecycle as container_lifecycle
from hydrahive.containers import reconciler as container_reconciler
from hydrahive.containers.incus_client import IncusError
from hydrahive.containers.models import Container
from hydrahive.vms import lifecycle as vm_lifecycle
from hydrahive.vms import reconciler as vm_reconciler
from hydrahive.vms.models import VM


def _container(*, node_id: str = "local") -> Container:
    return Container(
        container_id="container-1",
        owner="admin",
        name="placed-container",
        image="images:debian/12",
        network_mode="bridged",
        desired_state="running",
        actual_state="running",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        node_id=node_id,
    )


def _vm(*, node_id: str = "local", runtime: str = "qemu") -> VM:
    return VM(
        vm_id="vm-1",
        owner="admin",
        name="placed-vm",
        cpu=2,
        ram_mb=2048,
        disk_gb=20,
        qcow2_path="/tmp/placed-vm.qcow2",
        network_mode="bridged",
        desired_state="running",
        actual_state="running",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        node_id=node_id,
        runtime=runtime,
    )


def test_container_reconciler_ignores_remote_resources(monkeypatch) -> None:
    updates: list[tuple] = []

    monkeypatch.setattr(container_reconciler.incus, "is_available", lambda: True)

    async def running_names() -> set[str]:
        return set()

    monkeypatch.setattr(container_reconciler.incus, "list_running_names", running_names)
    monkeypatch.setattr(container_reconciler.cdb, "list_", lambda owner=None: [_container(node_id="node-a")])
    monkeypatch.setattr(
        container_reconciler.cdb, "update_state", lambda *args, **kwargs: updates.append((args, kwargs))
    )

    asyncio.run(container_reconciler.reconcile_once())

    assert updates == []


def test_vm_reconciler_ignores_nonlocal_or_non_qemu_resources(monkeypatch) -> None:
    updates: list[tuple] = []
    pid_checks: list[int | None] = []

    monkeypatch.setattr(
        vm_reconciler,
        "list_vms",
        lambda owner=None: [_vm(node_id="node-a"), _vm(runtime="incus")],
    )
    monkeypatch.setattr(vm_reconciler, "_pid_alive", lambda pid: pid_checks.append(pid) or False)
    monkeypatch.setattr(vm_reconciler, "update_vm_state", lambda *args, **kwargs: updates.append((args, kwargs)))
    monkeypatch.setattr(vm_reconciler.vnc, "cleanup_orphans", lambda tokens: None)

    asyncio.run(vm_reconciler.reconcile_once())

    assert pid_checks == []
    assert updates == []


def test_reconcilers_still_process_local_resources(monkeypatch) -> None:
    container_updates: list[tuple] = []
    vm_updates: list[tuple] = []

    monkeypatch.setattr(container_reconciler.incus, "is_available", lambda: True)

    async def running_names() -> set[str]:
        return set()

    monkeypatch.setattr(container_reconciler.incus, "list_running_names", running_names)
    monkeypatch.setattr(container_reconciler.cdb, "list_", lambda owner=None: [_container()])
    monkeypatch.setattr(
        container_reconciler.cdb,
        "update_state",
        lambda *args, **kwargs: container_updates.append((args, kwargs)),
    )
    monkeypatch.setattr(vm_reconciler, "list_vms", lambda owner=None: [_vm()])
    monkeypatch.setattr(vm_reconciler, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(
        vm_reconciler,
        "update_vm_state",
        lambda *args, **kwargs: vm_updates.append((args, kwargs)),
    )
    monkeypatch.setattr(vm_reconciler.vnc, "cleanup_orphans", lambda tokens: None)

    asyncio.run(container_reconciler.reconcile_once())
    asyncio.run(vm_reconciler.reconcile_once())

    assert len(container_updates) == 1
    assert len(vm_updates) == 1


@pytest.mark.parametrize("operation", ["create_and_start", "start", "stop", "restart_", "delete"])
def test_container_local_lifecycle_rejects_remote_resources(monkeypatch, operation: str) -> None:
    monkeypatch.setattr(container_lifecycle.cdb, "get", lambda container_id: _container(node_id="node-a"))

    with pytest.raises(IncusError, match="container_not_local"):
        asyncio.run(getattr(container_lifecycle, operation)("container-1"))


@pytest.mark.parametrize("operation", ["start", "shutdown"])
@pytest.mark.parametrize(("node_id", "runtime"), [("node-a", "qemu"), ("local", "incus")])
def test_vm_local_lifecycle_rejects_remote_resources(monkeypatch, operation: str, node_id: str, runtime: str) -> None:
    monkeypatch.setattr(
        vm_lifecycle,
        "get_vm",
        lambda vm_id: _vm(node_id=node_id, runtime=runtime),
    )

    with pytest.raises(vm_lifecycle.VMLifecycleError, match="vm_not_local"):
        asyncio.run(getattr(vm_lifecycle, operation)("vm-1"))
