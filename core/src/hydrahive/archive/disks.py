"""Platten, auf die das Archiv umziehen kann (Spec archiv-system.md, Etappe 1b).

Kein freies Pfadfeld: Die Admin-Konsole bietet nur diese Liste an, die API nimmt nur deren IDs. Gleiche Regeln
wie im Root-Runner (installer/lib/archive-disk.sh), der die Platte bei Bedarf für HydraHive einrichtet:
- echtes lokales Dateisystem, schreibbar eingehängt, Wurzel des Dateisystems (kein Bind-Mount)
- je Gerät nur einmal (kürzester Einhängepunkt)
- nicht: /boot*, /home, /root, /tmp, /var/tmp, alles unter /proc /sys /dev /run, nichts unter workspaces
ID = die ersten 12 Hex-Zeichen von sha256(einhängepunkt) – kein Pfad, gleich in Python und Shell.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from hydrahive.settings import settings

MOUNTINFO = Path("/proc/self/mountinfo")
FSTYPES = frozenset({"ext2", "ext3", "ext4", "xfs", "btrfs", "zfs", "f2fs", "bcachefs"})
BLOCKED = ("/boot", "/home", "/root", "/tmp", "/var/tmp", "/proc", "/sys", "/dev", "/run", "/etc", "/usr")
TARGET_NAME = "hydrahive-archiv"


def disk_id(mount: str) -> str:
    return hashlib.sha256(mount.encode()).hexdigest()[:12]


def _unescape(s: str) -> str:
    """mountinfo maskiert Leerzeichen, Tab, Zeilenumbruch und Backslash oktal (\\040 …)."""
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and s[i + 1:i + 4].isdigit() and len(s[i + 1:i + 4]) == 3:
            out.append(chr(int(s[i + 1:i + 4], 8)))
            i += 4
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _blocked(mount: str) -> bool:
    if mount == "/":
        return False
    if any(mount == b or mount.startswith(b + "/") for b in BLOCKED):
        return True
    ws = str(settings.workspaces_dir)
    return mount == ws or mount.startswith(ws + "/")


def _target(mount: str) -> str:
    return "/srv/" + TARGET_NAME if mount == "/" else f"{mount}/{TARGET_NAME}"


def _usage(path: str) -> tuple[int, int]:
    try:
        u = shutil.disk_usage(path)
        return u.total, u.free
    except OSError:
        return 0, 0


def _writable(path: Path) -> bool:
    """Darf HydraHive dort schreiben? Zielordner selbst, sonst der nächste vorhandene Elternordner."""
    p = Path(path)
    while not p.exists() and p != p.parent:
        p = p.parent
    return os.access(p, os.W_OK | os.X_OK)


def _parse(text: str) -> list[dict]:
    found: dict[str, dict] = {}
    for line in text.splitlines():
        left, sep, right = line.partition(" - ")
        f, r = left.split(), right.split()
        if not sep or len(f) < 6 or len(r) < 2:
            continue
        root, mount, opts = f[3], _unescape(f[4]), f[5].split(",")
        fstype, device = r[0], _unescape(r[1])
        if root != "/" or fstype not in FSTYPES or "rw" not in opts or _blocked(mount):
            continue
        prev = found.get(device)
        if prev is None or len(mount) < len(prev["mount"]):
            found[device] = {"mount": mount, "device": device, "fstype": fstype}
    return sorted(found.values(), key=lambda d: d["mount"])


def list_disks() -> list[dict]:
    try:
        text = MOUNTINFO.read_text()
    except OSError:
        return []
    disks = []
    for d in _parse(text):
        size, free = _usage(d["mount"])
        target = _target(d["mount"])
        disks.append({**d, "id": disk_id(d["mount"]), "path": target, "size_bytes": size, "free_bytes": free,
                      "writable": _writable(Path(target))})
    return disks


def find(disk: str) -> dict | None:
    return next((d for d in list_disks() if d["id"] == disk), None)


def allowed_mount(mount: str) -> bool:
    return any(d["mount"] == mount for d in list_disks())
