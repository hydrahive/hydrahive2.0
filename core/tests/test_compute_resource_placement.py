from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import asdict

import pytest
from fastapi import HTTPException

from hydrahive.api.routes import containers_crud, vms_lifecycle
from hydrahive.api.routes._container_helpers import ContainerCreate
from hydrahive.api.routes._vm_lifecycle_schemas import VMCreate
from hydrahive.compute import db as node_db
from hydrahive.containers import db as cdb
from hydrahive.containers.models import Container
from hydrahive.vms import _passthrough_db as passthrough_db
from hydrahive.vms import db as vmdb
from hydrahive.vms.models import VM


@pytest.fixture
def resource_db(tmp_path, monkeypatch):
    from hydrahive.db import init_db
    from hydrahive.settings import settings

    monkeypatch.setattr(settings, "sessions_db", tmp_path / "resources.db", raising=False)
    init_db()


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


def test_legacy_create_payloads_default_to_local() -> None:
    container = ContainerCreate(name="container", image="debian/12")
    vm = VMCreate(name="vm", cpu=1, ram_mb=512, disk_gb=5)

    assert container.node_id == "local"
    assert vm.node_id == "local"


def test_container_remote_placement_requires_admin() -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            containers_crud.create_container(
                ContainerCreate(name="remote-container", image="debian/12", node_id="node-a"),
                ("user", "user"),
            )
        )

    assert exc_info.value.status_code == 403


def test_vm_remote_placement_requires_admin() -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            vms_lifecycle.create_vm(
                VMCreate(name="remote-vm", cpu=1, ram_mb=512, disk_gb=5, node_id="node-a", image="debian/12"),
                ("user", "user"),
            )
        )

    assert exc_info.value.status_code == 403


def test_vm_remote_create_requires_image(monkeypatch) -> None:
    monkeypatch.setattr(
        vms_lifecycle.vmdb,
        "create_vm",
        lambda *args, **kwargs: pytest.fail("remote payload without image reached VM creation"),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            vms_lifecycle.create_vm(
                VMCreate(name="remote-vm", cpu=1, ram_mb=512, disk_gb=5, node_id="node-a"),
                ("admin", "admin"),
            )
        )

    assert exc_info.value.status_code == 400


def test_vm_remote_create_does_not_touch_local_qemu_disk(resource_db, monkeypatch) -> None:
    node_db.create_node(
        node_id="node-a",
        name="Node A",
        certificate_fingerprint="cd" * 32,
        capabilities={"incus": True, "kvm": True, "instance_types": ["container", "vm"]},
    )
    node_db.approve_node("node-a", "admin")
    node_db.transition_node_status("node-a", "online")

    async def fail_disk(*args, **kwargs):
        pytest.fail("remote VM create provisioned a local qcow2 disk")

    monkeypatch.setattr(vms_lifecycle.vmdisk, "create_qcow2", fail_disk)

    result = asyncio.run(
        vms_lifecycle.create_vm(
            VMCreate(name="remote-vm", cpu=2, ram_mb=2048, disk_gb=20, node_id="node-a", image="debian/12"),
            ("admin", "admin"),
        )
    )

    assert result["node_id"] == "node-a"
    assert result["runtime"] == "incus"
    assert result["image"] == "images:debian/12"
    assert result["actual_state"] == "starting"


def test_resource_serialization_includes_placement_and_runtime() -> None:
    container = asdict(_container(node_id="node-a"))
    vm = asdict(_vm(node_id="node-b", runtime="incus"))

    assert (container["node_id"], container["generation"]) == ("node-a", 0)
    assert (vm["node_id"], vm["generation"], vm["runtime"], vm["runtime_ref"]) == (
        "node-b",
        0,
        "incus",
        None,
    )


def test_container_db_mapper_persists_placement(resource_db) -> None:
    node_db.create_node(node_id="node-a", name="Node A")
    container = cdb.create(
        owner="admin",
        name="remote-container",
        image="images:debian/12",
        node_id="node-a",
    )

    assert (container.node_id, container.generation) == ("node-a", 0)


def test_vm_db_mapper_persists_placement_and_runtime(resource_db) -> None:
    node_db.create_node(node_id="node-a", name="Node A")
    vm = vmdb.create_vm(
        owner="admin",
        name="remote-vm",
        cpu=2,
        ram_mb=2048,
        disk_gb=20,
        qcow2_path="",
        node_id="node-a",
        runtime="incus",
        runtime_ref="instance-1",
    )

    assert (vm.node_id, vm.generation, vm.runtime, vm.runtime_ref) == (
        "node-a",
        0,
        "incus",
        "instance-1",
    )


def test_resource_placement_rejects_unknown_nodes_and_runtime_mismatches(resource_db) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="compute_node_not_found"):
        cdb.create(owner="admin", name="orphan", image="images:debian/12", node_id="missing")
    with pytest.raises(ValueError, match="local VMs require qemu"):
        vmdb.create_vm(
            owner="admin",
            name="invalid-runtime",
            cpu=1,
            ram_mb=512,
            disk_gb=5,
            qcow2_path="",
            runtime="incus",
        )


def test_resource_mutations_increment_generation(resource_db) -> None:
    container = cdb.create(owner="admin", name="container", image="images:debian/12")
    vm = vmdb.create_vm(owner="admin", name="vm", cpu=1, ram_mb=512, disk_gb=5, qcow2_path="")

    cdb.update_container_config(container.container_id, description="changed")
    cdb.update_state(container.container_id, desired="running")
    vmdb.update_vm_config(vm.vm_id, description="changed")
    vmdb.update_vm_state(vm.vm_id, desired="running")

    assert cdb.get(container.container_id).generation == 2
    assert vmdb.get_vm(vm.vm_id).generation == 2


def test_passthrough_mutations_increment_vm_generation(resource_db) -> None:
    vm = vmdb.create_vm(owner="admin", name="vm", cpu=1, ram_mb=512, disk_gb=5, qcow2_path="")

    disk = passthrough_db.insert(vm.vm_id, "/dev/fake", "test")
    assert vmdb.get_vm(vm.vm_id).generation == 1

    assert passthrough_db.remove(vm.vm_id, disk.passthrough_id) is True
    assert vmdb.get_vm(vm.vm_id).generation == 2
