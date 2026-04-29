"""qcow2-Disk-Erzeugung via qemu-img."""
from __future__ import annotations

import asyncio
from pathlib import Path

from hydrahive.settings import settings
from hydrahive.vms.qemu_args import qcow2_create_args


class DiskError(RuntimeError):
    def __init__(self, code: str, **params):
        super().__init__(f"{code}: {params}")
        self.code = code
        self.params = params


def disk_path_for(vm_id: str) -> Path:
    return settings.vms_disks_dir / f"{vm_id}.qcow2"


async def create_qcow2(vm_id: str, size_gb: int) -> Path:
    """Erzeugt sparse qcow2 in vms_disks_dir. Return: Pfad."""
    settings.vms_disks_dir.mkdir(parents=True, exist_ok=True)
    target = disk_path_for(vm_id)
    if target.exists():
        raise DiskError("qcow2_exists", path=str(target))
    try:
        proc = await asyncio.create_subprocess_exec(
            *qcow2_create_args(target, size_gb),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        raise DiskError("qemu_img_missing")
    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
    if proc.returncode != 0:
        raise DiskError("qcow2_create_failed",
                        rc=proc.returncode,
                        stderr=stderr.decode(errors="replace")[:300])
    return target


def remove_qcow2(vm_id: str) -> None:
    target = disk_path_for(vm_id)
    target.unlink(missing_ok=True)
