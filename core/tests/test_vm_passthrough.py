"""Tests für VM Passthrough-Disk-Feature."""
from __future__ import annotations

import pytest
from tests.conftest import bearer, error_code


# ---------------------------------------------------------------------------
# passthrough.py — Validation-Helpers
# ---------------------------------------------------------------------------

def test_validate_path_rejects_non_dev(tmp_path):
    """Pfade außerhalb von /dev/ werden abgelehnt."""
    from hydrahive.vms.passthrough import PassthroughError, _validate_path
    with pytest.raises(PassthroughError) as exc:
        _validate_path(str(tmp_path / "not_a_device"))
    assert exc.value.code == "path_not_in_dev"


def test_validate_path_rejects_traversal():
    """Path-Traversal-Versuch wird vom resolve() abgefangen."""
    from hydrahive.vms.passthrough import PassthroughError, _validate_path
    with pytest.raises(PassthroughError):
        _validate_path("/dev/../etc/passwd")


def test_validate_path_rejects_missing_device():
    """Nicht-existierendes Device unter /dev/ schlägt fehl."""
    from hydrahive.vms.passthrough import PassthroughError, _validate_path
    with pytest.raises(PassthroughError) as exc:
        _validate_path("/dev/zzznonexistent99")
    assert exc.value.code == "device_not_found"


# ---------------------------------------------------------------------------
# qemu_args.py — Passthrough-Disk-Args
# ---------------------------------------------------------------------------

def _make_vm():
    from hydrahive.vms.models import VM
    return VM(
        vm_id="vm-pt-test", owner="admin", name="pttest", cpu=2, ram_mb=2048, disk_gb=20,
        qcow2_path="/tmp/pt.qcow2", network_mode="bridged",
        disk_interface="virtio",
        desired_state="stopped", actual_state="created",
        created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
    )


def _make_passthrough(path: str, idx: int = 0):
    from hydrahive.vms.models import PassthroughDisk
    return PassthroughDisk(
        passthrough_id=f"pt-{idx}",
        vm_id="vm-pt-test",
        device_path=path,
        label=None,
        added_at="2026-01-01T00:00:00Z",
    )


def test_qemu_args_no_passthrough_by_default():
    """Ohne Passthrough-Disks kein ptdisk-Drive in den Args."""
    from hydrahive.vms.qemu_args import build_qemu_args
    args = build_qemu_args(_make_vm(), vnc_port=5950)
    assert not any("ptdisk" in a for a in args)


def test_qemu_args_passthrough_single():
    """Eine Passthrough-Disk erzeugt drive+device pair."""
    from hydrahive.vms.qemu_args import build_qemu_args
    disks = [_make_passthrough("/dev/sdb")]
    args = build_qemu_args(_make_vm(), vnc_port=5950, passthrough_disks=disks)
    # Drive
    assert any("file=/dev/sdb" in a and "format=raw" in a and "id=ptdisk0" in a for a in args)
    # Device
    assert any("virtio-blk-pci" in a and "drive=ptdisk0" in a for a in args)


def test_qemu_args_passthrough_multiple():
    """Mehrere Passthrough-Disks bekommen fortlaufende IDs."""
    from hydrahive.vms.qemu_args import build_qemu_args
    disks = [_make_passthrough("/dev/sdb", 0), _make_passthrough("/dev/sdc", 1)]
    args = build_qemu_args(_make_vm(), vnc_port=5950, passthrough_disks=disks)
    assert any("id=ptdisk0" in a for a in args)
    assert any("id=ptdisk1" in a for a in args)
    assert any("drive=ptdisk0" in a for a in args)
    assert any("drive=ptdisk1" in a for a in args)


def test_qemu_args_passthrough_uses_raw_format():
    """Passthrough-Disks nutzen format=raw, kein qcow2."""
    from hydrahive.vms.qemu_args import build_qemu_args
    disks = [_make_passthrough("/dev/sdb")]
    args = build_qemu_args(_make_vm(), vnc_port=5950, passthrough_disks=disks)
    assert any("format=raw" in a and "/dev/sdb" in a for a in args)
    # qcow2-format darf NICHT für Passthrough-Drive erscheinen
    drive_args = [a for a in args if "/dev/sdb" in a]
    assert all("format=qcow2" not in a for a in drive_args)


# ---------------------------------------------------------------------------
# DB — list_for_vm / add / remove
# ---------------------------------------------------------------------------

def test_list_for_vm_empty(client):
    """Neue VM hat keine Passthrough-Disks."""
    from hydrahive.vms import passthrough as pt
    from hydrahive.vms.db import create_vm
    from hydrahive.vms.disk import disk_path_for
    # Minimal-VM anlegen
    vm = create_vm("admin", "ptdbtest", 1, 512, 10,
                   str(disk_path_for("ptdbtest")), "bridged")
    disks = pt.list_for_vm(vm.vm_id)
    assert disks == []


def test_remove_nonexistent_raises(client):
    """Löschen einer nicht existierenden Disk wirft PassthroughError."""
    from hydrahive.vms import passthrough as pt
    with pytest.raises(pt.PassthroughError) as exc:
        pt.remove("vm-doesnt-exist", "pt-doesnt-exist")
    assert exc.value.code == "not_found"


# ---------------------------------------------------------------------------
# API — host-disks endpoint (admin only)
# ---------------------------------------------------------------------------

def test_host_disks_requires_admin(client, admin_headers, auth_headers):
    """Nur Admins dürfen host-disks abrufen."""
    resp = client.get("/api/vms/host-disks", headers=auth_headers)
    assert resp.status_code == 403
    assert error_code(resp) == "admin_only"

    # Admin bekommt Antwort (lsblk läuft möglicherweise nicht in CI → 503 ok)
    resp_admin = client.get("/api/vms/host-disks", headers=admin_headers)
    assert resp_admin.status_code in (200, 503)


# ---------------------------------------------------------------------------
# API — passthrough-disks CRUD
# ---------------------------------------------------------------------------

def test_passthrough_disks_list_requires_admin(client, admin_headers, auth_headers):
    """Nur Admins dürfen Passthrough-Disks einer VM auflisten."""
    # VM erstellen
    resp = client.post("/api/vms", headers=admin_headers, json={
        "name": "pt-api-test", "cpu": 1, "ram_mb": 512, "disk_gb": 5,
        "network_mode": "isolated",
    })
    assert resp.status_code == 201
    vm_id = resp.json()["vm_id"]

    # User darf nicht
    r = client.get(f"/api/vms/{vm_id}/passthrough-disks", headers=auth_headers)
    assert r.status_code == 403

    # Admin darf
    r = client.get(f"/api/vms/{vm_id}/passthrough-disks", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_passthrough_add_invalid_path(client, admin_headers):
    """Pfade außerhalb /dev/ werden von der API abgelehnt."""
    resp = client.post("/api/vms", headers=admin_headers, json={
        "name": "pt-invalid-test", "cpu": 1, "ram_mb": 512, "disk_gb": 5,
        "network_mode": "isolated",
    })
    assert resp.status_code == 201
    vm_id = resp.json()["vm_id"]

    r = client.post(f"/api/vms/{vm_id}/passthrough-disks", headers=admin_headers,
                    json={"device_path": "/tmp/not_a_device"})
    assert r.status_code == 400
    assert error_code(r) in ("path_not_in_dev", "device_not_found", "not_block_device")


def test_passthrough_add_requires_stopped_vm(client, admin_headers):
    """Passthrough-Disk kann nur zu gestoppter VM hinzugefügt werden."""
    resp = client.post("/api/vms", headers=admin_headers, json={
        "name": "pt-running-test", "cpu": 1, "ram_mb": 512, "disk_gb": 5,
        "network_mode": "isolated",
    })
    vm_id = resp.json()["vm_id"]

    # VM als running markieren (DB direkt, kein QEMU nötig)
    from hydrahive.vms.db import update_vm_state
    update_vm_state(vm_id, actual="running")

    r = client.post(f"/api/vms/{vm_id}/passthrough-disks", headers=admin_headers,
                    json={"device_path": "/dev/sdb"})
    assert r.status_code == 409
    assert error_code(r) == "vm_must_be_stopped"


def test_passthrough_remove_requires_stopped_vm(client, admin_headers):
    """Passthrough-Disk kann nur von gestoppter VM entfernt werden."""
    resp = client.post("/api/vms", headers=admin_headers, json={
        "name": "pt-rm-run-test", "cpu": 1, "ram_mb": 512, "disk_gb": 5,
        "network_mode": "isolated",
    })
    vm_id = resp.json()["vm_id"]

    from hydrahive.vms.db import update_vm_state
    update_vm_state(vm_id, actual="running")

    r = client.delete(f"/api/vms/{vm_id}/passthrough-disks/pt-fake-id",
                      headers=admin_headers)
    assert r.status_code == 409
    assert error_code(r) == "vm_must_be_stopped"


def test_passthrough_migration_table_exists(client):
    """Nach init_db existiert vm_passthrough_disks-Tabelle."""
    from hydrahive.db.connection import db
    with db() as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert "vm_passthrough_disks" in tables
