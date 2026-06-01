"""Path-Traversal-Schutz für ISO-Filenames (Issue #179).

Exploit: PATCH /api/vms/{id} mit iso_filename='../../../../etc/passwd'.
resolve_iso sanitisiert intern zum Basename 'passwd.iso' (Existenz-Check besteht,
wenn diese Library-ISO existiert), gespeichert wurde aber der ROHE Wert — und
build_qemu_args mountete daraus /etc/passwd read-only als CD-ROM in die VM.

Doppelte Absicherung:
  1. update_vm speichert den sanitisierten Rückgabewert (wie der create-Pfad).
  2. build_qemu_args mountet nur ISOs, deren Pfad real unter vms_isos_dir liegt.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def stub_disk_create(monkeypatch):
    async def _fake_create(vm_id: str, size_gb: int) -> Path:
        return Path(f"/tmp/{vm_id}.qcow2")

    monkeypatch.setattr(
        "hydrahive.api.routes.vms_lifecycle.vmdisk.create_qcow2", _fake_create
    )


def _vm_with_iso(iso_filename: str | None):
    from hydrahive.vms.models import VM
    return VM(
        vm_id="vm-iso", owner="admin", name="t", cpu=1, ram_mb=512, disk_gb=10,
        qcow2_path="/tmp/t.qcow2", network_mode="bridged", disk_interface="virtio",
        machine_type="q35", network_device="virtio-net-pci", iso_filename=iso_filename,
        desired_state="stopped", actual_state="created",
        created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
    )


# --- Route: PATCH speichert sanitisierten Namen, nicht den Rohwert ---------

def test_patch_vm_iso_traversal_is_sanitized(client, admin_headers, stub_disk_create):
    from hydrahive.settings import settings

    cr = client.post("/api/vms", headers=admin_headers, json={
        "name": "isovm", "cpu": 1, "ram_mb": 512, "disk_gb": 5, "network_mode": "bridged",
    })
    assert cr.status_code == 201, cr.text
    vm_id = cr.json()["vm_id"]

    settings.vms_isos_dir.mkdir(parents=True, exist_ok=True)
    (settings.vms_isos_dir / "passwd.iso").write_bytes(b"\x00")

    pr = client.patch(f"/api/vms/{vm_id}", headers=admin_headers, json={
        "iso_filename": "../../../../etc/passwd",
    })
    assert pr.status_code == 200, pr.text
    assert pr.json()["iso_filename"] == "passwd.iso", "Rohwert darf nicht gespeichert werden"


# --- build_qemu_args: Defense-in-Depth gegen Traversal in der DB -----------

def test_qemu_args_refuses_traversal_iso(client):
    from hydrahive.settings import settings
    from hydrahive.vms.qemu_args import build_qemu_args

    settings.vms_isos_dir.mkdir(parents=True, exist_ok=True)
    # real existierende Datei AUSSERHALB der isos-Dir (im Parent vms_dir)
    secret = settings.vms_dir / "secret.txt"
    secret.write_bytes(b"top-secret")
    assert secret.exists()

    args = build_qemu_args(_vm_with_iso("../secret.txt"), vnc_port=5950)

    assert not any("media=cdrom" in a for a in args), "Traversal-Datei darf nicht gemountet werden"
    assert "order=c,menu=on" in args, "ohne gültige ISO Boot nur von Disk"


def test_qemu_args_mounts_library_iso(client):
    from hydrahive.settings import settings
    from hydrahive.vms.qemu_args import build_qemu_args

    settings.vms_isos_dir.mkdir(parents=True, exist_ok=True)
    (settings.vms_isos_dir / "ok.iso").write_bytes(b"\x00")
    args = build_qemu_args(_vm_with_iso("ok.iso"), vnc_port=5950)

    drive = [a for a in args if "media=cdrom" in a]
    assert drive, "gültige Library-ISO muss gemountet werden"
    assert str(settings.vms_isos_dir / "ok.iso") in drive[0]
