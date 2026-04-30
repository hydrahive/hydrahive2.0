"""Live-Stats für VMs aus /proc — kein QMP nötig.

Wir kennen die PID aus der DB. /proc/<pid>/stat liefert CPU-Ticks (utime+stime),
/proc/<pid>/status liefert VmRSS. CPU-% kommt durch Differenz zweier Snapshots
geteilt durch Zeitdifferenz und Anzahl der CPUs.

Letzten Snapshot pro VM halten wir im Modul-State (in-memory). Reicht für
die UI — bei Backend-Restart fängt der Counter neu an.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

# {vm_id: (timestamp_ns, total_ticks, num_threads)}
_LAST: dict[str, tuple[float, int, int]] = {}

_CLK_TCK = os.sysconf("SC_CLK_TCK")
_NUM_CPUS = os.cpu_count() or 1


def read_stats(vm_id: str, pid: int | None) -> dict:
    """Returns {alive, cpu_pct, rss_mb, uptime_s}.

    cpu_pct ist beim ersten Aufruf 0 (kein delta). Aufrufe sollten ~3s
    auseinander liegen für stabile Werte.
    """
    if pid is None:
        return {"alive": False, "cpu_pct": 0, "rss_mb": 0, "uptime_s": 0}
    proc = Path("/proc") / str(pid)
    try:
        stat_line = (proc / "stat").read_text()
    except (FileNotFoundError, PermissionError):
        _LAST.pop(vm_id, None)
        return {"alive": False, "cpu_pct": 0, "rss_mb": 0, "uptime_s": 0}

    # /proc/<pid>/stat felder: pid (comm) state ppid pgrp session tty_nr tpgid flags
    # minflt cminflt majflt cmajflt utime(14) stime(15) cutime(16) cstime(17) ...
    # comm kann Spaces enthalten — splitten an letztem ')'
    rparen = stat_line.rfind(")")
    rest = stat_line[rparen + 2:].split()
    utime = int(rest[11])
    stime = int(rest[12])
    starttime = int(rest[19])
    total = utime + stime

    # /proc/uptime → seconds since boot
    try:
        uptime_total = float((Path("/proc") / "uptime").read_text().split()[0])
        proc_uptime = uptime_total - starttime / _CLK_TCK
    except Exception:
        proc_uptime = 0.0

    # RSS aus status (kB)
    rss_mb = 0
    try:
        for line in (proc / "status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                rss_mb = int(line.split()[1]) // 1024
                break
    except (FileNotFoundError, PermissionError):
        pass

    now = time.monotonic()
    cpu_pct = 0
    last = _LAST.get(vm_id)
    if last:
        dt = now - last[0]
        if dt > 0.1:
            dticks = total - last[1]
            cpu_pct = round((dticks / _CLK_TCK) / dt * 100 / _NUM_CPUS, 1)
            cpu_pct = max(0, min(cpu_pct * _NUM_CPUS, 100 * _NUM_CPUS))  # Multi-vCPU sichtbar
    _LAST[vm_id] = (now, total, 0)

    return {
        "alive": True,
        "cpu_pct": cpu_pct,
        "rss_mb": rss_mb,
        "uptime_s": int(proc_uptime),
    }


def forget(vm_id: str) -> None:
    _LAST.pop(vm_id, None)
