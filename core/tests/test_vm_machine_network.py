"""Per-VM machine_type + network_device — Migration, API, qemu_args.

Hintergrund: HH1 hatte beide Switches mit explizitem Code-Kommentar
("q35 bricht FreeBSD/ältere Gäste beim Import" + "e1000 statt virtio:
VBox/VMware erwarten em0"). HH2 hardcoded q35 + virtio-net-pci → ZFS-MOS-
Bootfehler bei FreeBSD-Imports + kein Netz bei Imports ohne virtio-Treiber.
"""
from __future__ import annotations

import pytest


def _make_vm(machine_type: str = "q35", network_device: str = "virtio-net-pci",
             network_mode: str = "bridged"):
    from hydrahive.vms.models import VM
    return VM(
        vm_id="vm-test", owner="admin", name="t", cpu=2, ram_mb=2048, disk_gb=20,
        qcow2_path="/tmp/test.qcow2", network_mode=network_mode,
        disk_interface="virtio",
        machine_type=machine_type, network_device=network_device,
        desired_state="stopped", actual_state="created",
        created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# qemu_args.py — machine + network_device im Output
# ---------------------------------------------------------------------------

def test_qemu_args_machine_q35_default():
    from hydrahive.vms.qemu_args import build_qemu_args
    args = build_qemu_args(_make_vm("q35"), vnc_port=5950)
    # Wir müssen auch das nachfolgende Argument zu -machine prüfen
    idx = args.index("-machine")
    machine_arg = args[idx + 1]
    assert machine_arg.startswith("q35,")


def test_qemu_args_machine_pc_for_freebsd():
    from hydrahive.vms.qemu_args import build_qemu_args
    args = build_qemu_args(_make_vm("pc"), vnc_port=5950)
    idx = args.index("-machine")
    machine_arg = args[idx + 1]
    assert machine_arg.startswith("pc,")


def test_qemu_args_network_device_virtio_default():
    from hydrahive.vms.qemu_args import build_qemu_args
    args = build_qemu_args(_make_vm(network_device="virtio-net-pci"), vnc_port=5950)
    # -device <NIC>,netdev=net0,mac=...
    nic_args = [a for a in args if "netdev=net0" in a and "mac=" in a]
    assert nic_args, "kein NIC-Device mit netdev=net0+mac gefunden"
    assert any("virtio-net-pci" in a for a in nic_args)


def test_qemu_args_network_device_e1000_for_imports():
    from hydrahive.vms.qemu_args import build_qemu_args
    args = build_qemu_args(_make_vm(network_device="e1000"), vnc_port=5950)
    nic_args = [a for a in args if "netdev=net0" in a and "mac=" in a]
    assert nic_args
    assert any(a.startswith("e1000,") for a in nic_args)
    # virtio-net-pci darf nicht als NIC drin sein
    assert not any("virtio-net-pci" in a for a in nic_args)


def test_qemu_args_e1000_works_for_isolated_mode():
    """e1000 wird auch im isolated-Mode korrekt angewendet."""
    from hydrahive.vms.qemu_args import build_qemu_args
    args = build_qemu_args(
        _make_vm(network_device="e1000", network_mode="isolated"),
        vnc_port=5950,
    )
    nic_args = [a for a in args if "netdev=net0" in a and "mac=" in a]
    assert nic_args
    assert any(a.startswith("e1000,") for a in nic_args)


# ---------------------------------------------------------------------------
# Migration 009 — Spalten existieren mit Default
# ---------------------------------------------------------------------------

def test_migration_009_adds_machine_type_and_network_device(client):
    from hydrahive.db.connection import db
    with db() as conn:
        cols = {row[1]: row for row in conn.execute("PRAGMA table_info(vms)").fetchall()}
    for col, default in (("machine_type", "'q35'"),
                         ("network_device", "'virtio-net-pci'")):
        assert col in cols, f"{col} column missing"
        assert cols[col][2] == "TEXT"
        assert cols[col][3] == 1  # NOT NULL
        assert cols[col][4] == default


def test_existing_vms_default_to_q35_and_virtio_net(client):
    from hydrahive.vms import db as vmdb
    vm = vmdb.create_vm(
        owner="admin", name="defaultvm2", cpu=1, ram_mb=512, disk_gb=10,
        qcow2_path="/tmp/dummy.qcow2",
    )
    assert vm.machine_type == "q35"
    assert vm.network_device == "virtio-net-pci"


# ---------------------------------------------------------------------------
# API — Create + Update
# ---------------------------------------------------------------------------

@pytest.fixture
def stub_disk_create(monkeypatch):
    from pathlib import Path

    async def _fake_create(vm_id: str, size_gb: int) -> Path:
        return Path(f"/tmp/{vm_id}.qcow2")

    monkeypatch.setattr("hydrahive.api.routes.vms_lifecycle.vmdisk.create_qcow2", _fake_create)


def test_create_vm_with_pc_e1000_persists(client, admin_headers, stub_disk_create):
    """POST /api/vms mit machine_type=pc + e1000 schreibt beide Felder."""
    r = client.post("/api/vms", headers=admin_headers, json={
        "name": "freebsdVm", "cpu": 1, "ram_mb": 512, "disk_gb": 5,
        "network_mode": "bridged",
        "machine_type": "pc", "network_device": "e1000",
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["machine_type"] == "pc"
    assert data["network_device"] == "e1000"


def test_create_vm_invalid_machine_type_400(client, admin_headers, stub_disk_create):
    r = client.post("/api/vms", headers=admin_headers, json={
        "name": "badmach", "cpu": 1, "ram_mb": 512, "disk_gb": 5,
        "network_mode": "bridged", "machine_type": "microvm",
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "vm_machine_type_invalid"


def test_create_vm_invalid_network_device_400(client, admin_headers, stub_disk_create):
    r = client.post("/api/vms", headers=admin_headers, json={
        "name": "badnic", "cpu": 1, "ram_mb": 512, "disk_gb": 5,
        "network_mode": "bridged", "network_device": "rtl8139",
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "vm_network_device_invalid"


def test_patch_vm_to_pc_e1000(client, admin_headers, stub_disk_create):
    cr = client.post("/api/vms", headers=admin_headers, json={
        "name": "switch", "cpu": 1, "ram_mb": 512, "disk_gb": 5,
        "network_mode": "bridged",
    })
    vm_id = cr.json()["vm_id"]

    pr = client.patch(f"/api/vms/{vm_id}", headers=admin_headers, json={
        "machine_type": "pc", "network_device": "e1000",
    })
    assert pr.status_code == 200, pr.text
    j = pr.json()
    assert j["machine_type"] == "pc"
    assert j["network_device"] == "e1000"
