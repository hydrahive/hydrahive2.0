"""Prüfung „System“ für /api/system/health: offene Systemupdates und „Neustart nötig“.

docs/specs/system-updates.md (Task f24c39bf): Auf .2 standen 25 Pakete und ein Rechner-Neustart offen, ohne
dass es jemand sah. Die Zählung läuft als Dienst-Nutzer ohne Sperre (apt-get -s), zwischengespeichert, weil
die Admin-Konsole alle 10 s fragt. Die Neustart-Marke wird immer frisch geprüft (billig).
"""
from __future__ import annotations

import shutil
import subprocess
import threading
import time

from hydrahive.settings import settings

CACHE_SECONDS = 15 * 60
_cache: dict[str, tuple[float, int | None]] = {}
_lock = threading.Lock()


def _pending_count() -> int | None:
    """Anzahl Pakete, die das nächste Update anheben würde; None = unbekannt."""
    with _lock:
        hit = _cache.get("pending")
        now = time.monotonic()
        if hit and now - hit[0] < CACHE_SECONDS:
            return hit[1]
        try:
            r = subprocess.run(
                ["apt-get", "-s", "-o", "Debug::NoLocking=1", "upgrade", "--with-new-pkgs"],
                capture_output=True, text=True, timeout=60, env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            )
            count = sum(1 for line in r.stdout.splitlines() if line.startswith("Inst ")) if r.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            count = None
        _cache["pending"] = (now, count)
        return count


def check_system_updates() -> dict | None:
    if not shutil.which("apt-get"):
        return None   # kein apt (Mac) → keine Prüfung
    count = _pending_count()
    reboot = settings.reboot_required_file.exists()
    base = {"name_code": "system_updates"}
    if count is None:
        return {**base, "ok": False, "detail_code": "sysupd_unknown"}
    if count and reboot:
        return {**base, "ok": False, "detail_code": "sysupd_pending_reboot", "params": {"count": count}}
    if count:
        return {**base, "ok": False, "detail_code": "sysupd_pending", "params": {"count": count}}
    if reboot:
        return {**base, "ok": False, "detail_code": "sysupd_reboot"}
    return {**base, "ok": True, "detail_code": "sysupd_ok"}
