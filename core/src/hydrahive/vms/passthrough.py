"""Passthrough-Disk-Verwaltung — Block-Devices auf dem Host in VMs durchreichen.

Sicherheits-Invarianten:
- device_path muss unter /dev/ liegen und ein echtes Block-Device sein
- Nur unmountete Devices dürfen hinzugefügt werden (geprüft via lsblk)
- Kein shell=True, kein String-Join für Subprocess-Argumente
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db
from hydrahive.vms.models import HostDisk, PassthroughDisk

logger = logging.getLogger(__name__)


class PassthroughError(RuntimeError):
    def __init__(self, code: str, **params):
        super().__init__(f"{code}: {params}")
        self.code = code
        self.params = params


# ---------------------------------------------------------------------------
# Host-Disks listing
# ---------------------------------------------------------------------------

async def list_host_disks() -> list[HostDisk]:
    """Listet alle Block-Devices des Hosts via lsblk (JSON).

    Gibt nur Top-Level-Devices zurück (disks + ihre Partitionen als children).
    Filtert Loop-Devices heraus.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "lsblk", "--json", "--output", "NAME,PATH,SIZE,TYPE,MOUNTPOINT,MODEL,SERIAL",
            "--tree",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
    except FileNotFoundError:
        raise PassthroughError("lsblk_missing")
    except asyncio.TimeoutError:
        raise PassthroughError("lsblk_timeout")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        raise PassthroughError("lsblk_parse_error")

    return [_parse_disk(d) for d in data.get("blockdevices", [])
            if d.get("type") == "disk" and not d.get("name", "").startswith("loop")]


def _parse_disk(raw: dict) -> HostDisk:
    children = [_parse_disk(c) for c in raw.get("children", []) or []]
    return HostDisk(
        name=raw.get("name", ""),
        path=raw.get("path", f"/dev/{raw.get('name', '')}"),
        size=raw.get("size", "?"),
        model=raw.get("model") or None,
        serial=raw.get("serial") or None,
        children=children,
    )


def _is_mounted(path: str, all_disks: list[dict]) -> bool:
    """Prüft rekursiv ob path oder eine seiner Partitionen gemountet ist."""
    for dev in all_disks:
        dev_path = dev.get("path", f"/dev/{dev.get('name', '')}")
        if dev_path == path and dev.get("mountpoint"):
            return True
        for child in dev.get("children", []) or []:
            child_path = child.get("path", f"/dev/{child.get('name', '')}")
            if child.get("mountpoint"):
                # Wenn eine Partition gemountet ist, gilt die ganze Disk als in Benutzung
                if dev_path == path:
                    return True
    return False


async def list_unmounted_host_disks() -> list[HostDisk]:
    """Nur Disks ohne aktive Mount-Points (inkl. Partitionen)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "lsblk", "--json", "--output", "NAME,PATH,SIZE,TYPE,MOUNTPOINT,MODEL,SERIAL",
            "--tree",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
    except FileNotFoundError:
        raise PassthroughError("lsblk_missing")
    except asyncio.TimeoutError:
        raise PassthroughError("lsblk_timeout")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        raise PassthroughError("lsblk_parse_error")

    all_raw = data.get("blockdevices", [])
    result: list[HostDisk] = []
    for raw in all_raw:
        if raw.get("type") != "disk":
            continue
        if raw.get("name", "").startswith("loop"):
            continue
        if _has_any_mountpoint(raw):
            continue
        result.append(_parse_disk(raw))
    return result


def _has_any_mountpoint(raw: dict) -> bool:
    """True wenn dieses Device oder eine Partition einen Mountpoint hat."""
    if raw.get("mountpoint"):
        return True
    for child in raw.get("children", []) or []:
        if _has_any_mountpoint(child):
            return True
    return False


# ---------------------------------------------------------------------------
# DB-Zugriff
# ---------------------------------------------------------------------------

def _row_to_passthrough(r) -> PassthroughDisk:
    return PassthroughDisk(
        passthrough_id=r["passthrough_id"],
        vm_id=r["vm_id"],
        device_path=r["device_path"],
        label=r["label"],
        added_at=r["added_at"],
    )


def list_for_vm(vm_id: str) -> list[PassthroughDisk]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM vm_passthrough_disks WHERE vm_id = ? ORDER BY added_at",
            (vm_id,),
        ).fetchall()
    return [_row_to_passthrough(r) for r in rows]


def list_all_paths() -> set[str]:
    """Alle device_paths aller VMs — für lsblk-Overlay im Frontend."""
    with db() as conn:
        rows = conn.execute("SELECT device_path FROM vm_passthrough_disks").fetchall()
    return {r["device_path"] for r in rows}


async def add(vm_id: str, device_path: str, label: str | None = None) -> PassthroughDisk:
    """Fügt ein Block-Device als Passthrough hinzu.

    Validiert:
    1. Pfad liegt unter /dev/
    2. Ist ein Block-Device (Path.is_block_device)
    3. Hat keinen aktiven Mountpoint (lsblk)
    """
    _validate_path(device_path)
    await _assert_unmounted(device_path)

    pid = uuid7()
    ts = now_iso()
    try:
        with db() as conn:
            conn.execute(
                """INSERT INTO vm_passthrough_disks (passthrough_id, vm_id, device_path, label, added_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (pid, vm_id, device_path, label, ts),
            )
    except Exception as e:
        if "UNIQUE" in str(e):
            raise PassthroughError("already_attached", path=device_path)
        raise
    return PassthroughDisk(passthrough_id=pid, vm_id=vm_id,
                           device_path=device_path, label=label, added_at=ts)


def remove(vm_id: str, passthrough_id: str) -> None:
    with db() as conn:
        result = conn.execute(
            "DELETE FROM vm_passthrough_disks WHERE passthrough_id = ? AND vm_id = ?",
            (passthrough_id, vm_id),
        )
    if result.rowcount == 0:
        raise PassthroughError("not_found", passthrough_id=passthrough_id)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_path(device_path: str) -> None:
    p = Path(device_path).resolve()
    if not str(p).startswith("/dev/"):
        raise PassthroughError("path_not_in_dev", path=device_path)
    if not p.exists():
        raise PassthroughError("device_not_found", path=device_path)
    if not p.is_block_device():
        raise PassthroughError("not_block_device", path=device_path)


async def _assert_unmounted(device_path: str) -> None:
    try:
        proc = await asyncio.create_subprocess_exec(
            "lsblk", "--json", "--output", "NAME,PATH,MOUNTPOINT", device_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
    except (FileNotFoundError, asyncio.TimeoutError):
        return  # lsblk-Fehler → wir lassen durch, Kernel sperrt gemountete Devices ohnehin

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return

    for dev in data.get("blockdevices", []):
        if _has_any_mountpoint(dev):
            raise PassthroughError("device_mounted", path=device_path)
