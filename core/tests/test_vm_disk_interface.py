"""Per-VM disk_interface (virtio/sata/ide) — Migration, API, qemu_args."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# qemu_args.py — Disk-Args je nach Interface
# ---------------------------------------------------------------------------

def _make_vm(disk_interface: str = "virtio"):
    from hydrahive.vms.models import VM
    return VM(
        vm_id="vm-test", owner="admin", name="t", cpu=2, ram_mb=2048, disk_gb=20,
        qcow2_path="/tmp/test.qcow2", network_mode="bridged",
        disk_interface=disk_interface,
        desired_state="stopped", actual_state="created",
        created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
    )


def test_qemu_args_virtio_default():
    from hydrahive.vms.qemu_args import build_qemu_args
    args = build_qemu_args(_make_vm("virtio"), vnc_port=5950)
    assert any("if=virtio" in a for a in args)
    # Kein ahci/ide-hd device bei virtio
    assert not any("ahci" in a for a in args)
    assert not any("ide-hd" in a for a in args)


def test_qemu_args_sata_uses_ahci():
    from hydrahive.vms.qemu_args import build_qemu_args
    args = build_qemu_args(_make_vm("sata"), vnc_port=5950)
    assert any("if=none" in a and "id=disk0" in a for a in args)
    assert "ahci,id=ahci" in args
    assert "ide-hd,bus=ahci.0,drive=disk0" in args
    # virtio darf nicht im Disk-Drive sein
    assert not any("if=virtio" in a and "disk" in a for a in args)


def test_qemu_args_ide_legacy():
    from hydrahive.vms.qemu_args import build_qemu_args
    args = build_qemu_args(_make_vm("ide"), vnc_port=5950)
    assert any("if=ide" in a for a in args)
    assert not any("ahci" in a for a in args)


# ---------------------------------------------------------------------------
# Migration — Column existiert mit Default 'virtio'
# ---------------------------------------------------------------------------

def test_migration_008_adds_disk_interface_column(client):
    """Nach init_db hat die vms-Tabelle eine disk_interface-Spalte mit Default."""
    from hydrahive.db.connection import db
    with db() as conn:
        cols = {row[1]: row for row in conn.execute("PRAGMA table_info(vms)").fetchall()}
    assert "disk_interface" in cols, f"disk_interface column missing — got: {list(cols.keys())}"
    # cid, name, type, notnull, dflt_value, pk
    assert cols["disk_interface"][2] == "TEXT"
    assert cols["disk_interface"][3] == 1  # NOT NULL
    assert cols["disk_interface"][4] == "'virtio'"


def test_existing_vms_default_to_virtio(client):
    """VMs ohne explizit gesetztes disk_interface bekommen 'virtio'."""
    from hydrahive.vms import db as vmdb
    vm = vmdb.create_vm(
        owner="admin", name="defaultvm", cpu=1, ram_mb=512, disk_gb=10,
        qcow2_path="/tmp/dummy.qcow2",
    )
    assert vm.disk_interface == "virtio"


# ---------------------------------------------------------------------------
# API — Create + Update mit disk_interface
# ---------------------------------------------------------------------------

@pytest.fixture
def stub_disk_create(monkeypatch):
    """qcow2-Erzeugung mocken — sonst braucht der Test qemu-img."""
    from pathlib import Path

    async def _fake_create(vm_id: str, size_gb: int) -> Path:
        return Path(f"/tmp/{vm_id}.qcow2")

    monkeypatch.setattr("hydrahive.api.routes.vms_lifecycle.vmdisk.create_qcow2", _fake_create)


def test_create_vm_with_sata_persists(client, admin_headers, stub_disk_create):
    """POST /api/vms mit disk_interface=sata schreibt das Feld in DB."""
    r = client.post("/api/vms", headers=admin_headers, json={
        "name": "sataVm", "cpu": 1, "ram_mb": 512, "disk_gb": 5,
        "network_mode": "bridged", "disk_interface": "sata",
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["disk_interface"] == "sata"


def test_create_vm_invalid_disk_interface_400(client, admin_headers, stub_disk_create):
    """POST mit unbekanntem Interface → 400 vm_disk_interface_invalid."""
    r = client.post("/api/vms", headers=admin_headers, json={
        "name": "badif", "cpu": 1, "ram_mb": 512, "disk_gb": 5,
        "network_mode": "bridged", "disk_interface": "scsi",
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "vm_disk_interface_invalid"


def test_create_vm_default_virtio_when_unset(client, admin_headers, stub_disk_create):
    """Wenn Body kein disk_interface enthält, kommt der Default virtio."""
    r = client.post("/api/vms", headers=admin_headers, json={
        "name": "implicitVm", "cpu": 1, "ram_mb": 512, "disk_gb": 5,
        "network_mode": "bridged",
    })
    assert r.status_code == 201, r.text
    assert r.json()["disk_interface"] == "virtio"


def test_patch_vm_disk_interface_to_ide(client, admin_headers, stub_disk_create):
    """PATCH /api/vms/{id} mit disk_interface=ide — VM ist im 'created'-State, also editierbar."""
    cr = client.post("/api/vms", headers=admin_headers, json={
        "name": "patchif", "cpu": 1, "ram_mb": 512, "disk_gb": 5,
        "network_mode": "bridged", "disk_interface": "virtio",
    })
    vm_id = cr.json()["vm_id"]

    pr = client.patch(f"/api/vms/{vm_id}", headers=admin_headers, json={
        "disk_interface": "ide",
    })
    assert pr.status_code == 200, pr.text
    assert pr.json()["disk_interface"] == "ide"


def test_patch_vm_invalid_disk_interface_400(client, admin_headers, stub_disk_create):
    """PATCH mit unbekanntem Interface → 400."""
    cr = client.post("/api/vms", headers=admin_headers, json={
        "name": "patchbad", "cpu": 1, "ram_mb": 512, "disk_gb": 5,
        "network_mode": "bridged",
    })
    vm_id = cr.json()["vm_id"]

    pr = client.patch(f"/api/vms/{vm_id}", headers=admin_headers, json={
        "disk_interface": "nvme",
    })
    assert pr.status_code == 400
    assert pr.json()["detail"]["code"] == "vm_disk_interface_invalid"
