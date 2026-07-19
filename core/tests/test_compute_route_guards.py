from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from hydrahive.api.routes import (
    container_console,
    containers_ops,
    vms_ops,
    vms_passthrough,
    vms_snapshots,
    vms_vnc,
)
from hydrahive.containers.models import Container
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


@pytest.mark.parametrize(
    ("route", "incus_operation"),
    [
        (containers_ops.container_log, "show_log"),
        (containers_ops.container_config, "show_config"),
    ],
)
def test_container_inspection_routes_reject_remote_before_incus(monkeypatch, route, incus_operation: str) -> None:
    monkeypatch.setattr(
        containers_ops,
        "container_or_404",
        lambda *args: _container(node_id="node-a"),
    )

    async def fail_local_call(*args, **kwargs):
        pytest.fail("remote container reached local Incus")

    monkeypatch.setattr(containers_ops.incus, incus_operation, fail_local_call)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(route("container-1", ("admin", "admin")))

    assert exc_info.value.status_code == 400


def test_container_console_rejects_remote_before_session_start(monkeypatch) -> None:
    class FakeWebSocket:
        def __init__(self) -> None:
            self.closed: tuple[int, str | None] | None = None

        async def close(self, code: int, reason: str | None = None) -> None:
            self.closed = (code, reason)

        async def accept(self) -> None:
            pytest.fail("remote container console was accepted")

    websocket = FakeWebSocket()
    monkeypatch.setattr(container_console, "_authenticate", lambda token: ("admin", "admin"))
    monkeypatch.setattr(
        container_console.cdb,
        "get",
        lambda container_id: _container(node_id="node-a"),
    )

    asyncio.run(container_console.container_console(websocket, "container-1", "token"))

    assert websocket.closed == (4409, "container_not_local")


@pytest.mark.parametrize(
    ("module", "route"),
    [
        (vms_ops, vms_ops.vm_stats),
        (vms_ops, vms_ops.vm_log),
        (vms_vnc, vms_vnc.vnc_info),
    ],
)
def test_vm_local_data_routes_reject_remote(monkeypatch, module, route) -> None:
    monkeypatch.setattr(module, "vm_or_404", lambda *args: _vm(node_id="node-a", runtime="incus"))

    with pytest.raises(HTTPException) as exc_info:
        route("vm-1", ("admin", "admin"))

    assert exc_info.value.status_code == 400


@pytest.mark.parametrize("route", [vms_ops.stop_vm, vms_ops.poweroff_vm])
def test_vm_stop_routes_return_coded_error_for_remote(monkeypatch, route) -> None:
    monkeypatch.setattr(
        vms_ops,
        "vm_or_404",
        lambda *args: _vm(node_id="node-a", runtime="incus"),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(route("vm-1", ("admin", "admin")))

    assert exc_info.value.status_code == 400


def test_vm_snapshot_and_passthrough_routes_reject_remote_before_local_io(monkeypatch) -> None:
    remote = _vm(node_id="node-a", runtime="incus")
    monkeypatch.setattr(vms_snapshots, "vm_or_404", lambda *args: remote)
    monkeypatch.setattr(vms_passthrough, "vm_or_404", lambda *args: remote)

    with pytest.raises(HTTPException):
        asyncio.run(
            vms_snapshots.create_snapshot(
                "vm-1",
                vms_snapshots.SnapshotCreate(name="snapshot"),
                ("admin", "admin"),
            )
        )
    with pytest.raises(HTTPException):
        asyncio.run(
            vms_passthrough.add_passthrough_disk(
                "vm-1",
                vms_passthrough.AddPassthroughBody(device_path="/dev/fake"),
                ("admin", "admin"),
            )
        )
