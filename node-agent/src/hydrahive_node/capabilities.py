"""Bounded local capability and resource collection without shell execution."""

from __future__ import annotations

import os
import platform
import shutil
import socket
from pathlib import Path

INCUS_SOCKET = Path("/var/lib/incus/unix.socket")


def _memory() -> tuple[int, int]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            key, raw = line.split(":", 1)
            if key in {"MemTotal", "MemAvailable"}:
                values[key] = int(raw.strip().split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        return 0, 0
    return values.get("MemTotal", 0), values.get("MemAvailable", 0)


def collect() -> tuple[dict[str, object], dict[str, object], list[str]]:
    memory_total, memory_available = _memory()
    disk = shutil.disk_usage("/")
    kvm = Path("/dev/kvm")
    kvm_available = kvm.exists() and os.access(kvm, os.R_OK | os.W_OK)
    incus_available = INCUS_SOCKET.exists() and os.access(INCUS_SOCKET, os.R_OK | os.W_OK)
    health_errors: list[str] = []
    if not incus_available:
        health_errors.append("incus_unavailable")
    capabilities: dict[str, object] = {
        "hostname": socket.gethostname()[:255],
        "os": platform.platform()[:512],
        "architecture": platform.machine()[:64],
        "kvm": kvm_available,
        "incus": incus_available,
        "instance_types": ["container"] + (["vm"] if kvm_available else []),
        "network_profiles": [],
    }
    try:
        load_1m = os.getloadavg()[0]
    except OSError:
        load_1m = 0.0
    resources: dict[str, object] = {
        "cpu_cores": os.cpu_count() or 1,
        "cpu_load_1m": round(load_1m, 3),
        "memory_total_bytes": memory_total,
        "memory_available_bytes": memory_available,
        "storage_total_bytes": disk.total,
        "storage_free_bytes": disk.free,
    }
    return capabilities, resources, health_errors
