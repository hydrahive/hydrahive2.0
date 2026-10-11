"""Zustand der Zusatz-Module für das Admin-Cockpit (docs/specs/installer-core-first.md §3).

Nur lesend und ohne root: „installiert“ kommt aus einer Zustandsprüfung je Modul, „gewünscht“ aus install.conf
(die update.sh pflegt). Nachinstalliert wird über installer/addon-ctl.sh – die Liste dort muss zu ADDONS passen.
"""
from __future__ import annotations

import logging
import re
import shutil
import socket
from pathlib import Path
from typing import Callable

from hydrahive.communication.whatsapp._orphan import BRIDGE_DIR
from hydrahive.containers.incus_client import is_available as _incus_available
from hydrahive.samba.manager import samba_status
from hydrahive.voice.stt import STT_HOST, STT_PORT

logger = logging.getLogger(__name__)

# Feste Reihenfolge für die Oberfläche. Gleiche Namen wie in installer/addon-ctl.sh und lib/install-choices.sh.
ADDONS: tuple[str, ...] = ("containers", "vms", "samba", "whatsapp", "voice", "tailscale")
RESTARTS_SERVICE = frozenset({"vms", "containers"})          # 65-vms.sh / 70-containers.sh patchen hydrahive2.service
REQUIRES: dict[str, list[str]] = {"voice": ["containers"]}
WSL_LIMITED = frozenset({"vms", "containers", "voice"})

# Nur 65-vms.sh legt diese Unit an. qemu allein reicht nicht: incus zieht qemu-system-x86 als Abhängigkeit mit.
_VM_UNIT = Path("/etc/systemd/system/hydrahive2-websockify.service")
_WA_BRIDGE = BRIDGE_DIR
_STT = (STT_HOST, STT_PORT)
_PROC_VERSION = Path("/proc/version")
_WSL_INTEROP = Path("/proc/sys/fs/binfmt_misc/WSLInterop")
_CONF_LINE = re.compile(r"^(HH_INSTALL_[A-Z_]+)=['\"]?(yes|no)['\"]?\s*$")


def _vms_installed() -> bool:
    return _VM_UNIT.exists() and shutil.which("qemu-system-x86_64") is not None


def _whatsapp_installed() -> bool:
    return (_WA_BRIDGE / "node_modules").is_dir()


def _voice_installed() -> bool:
    """Whisper muss auf „describe“ antworten. Nur „Port offen“ reicht nicht: das incus-Proxy-Device nimmt Verbindungen
    auch an, wenn im Container kein Dienst läuft (Fund hh-instcore 11.10.2026)."""
    try:
        with socket.create_connection(_STT, timeout=1.0) as conn:
            conn.settimeout(1.5)
            conn.sendall(b'{"type": "describe"}\n')
            return conn.recv(64).startswith(b'{"type": "info"')
    except OSError:
        return False


PROBES: dict[str, Callable[[], bool]] = {
    "containers": _incus_available,
    "vms": _vms_installed,
    "samba": lambda: bool(samba_status()["installed"]),
    "whatsapp": _whatsapp_installed,
    "voice": _voice_installed,
    "tailscale": lambda: shutil.which("tailscale") is not None,
}


def is_wsl() -> bool:
    if _WSL_INTEROP.exists():
        return True
    try:
        return "microsoft" in _PROC_VERSION.read_text(errors="replace").lower()
    except OSError:
        return False


def _enabled(conf: Path) -> dict[str, bool]:
    try:
        text = conf.read_text(errors="replace")
    except OSError:
        return {}
    out: dict[str, bool] = {}
    for line in text.splitlines():
        m = _CONF_LINE.match(line.strip())
        if m:
            out[m.group(1)] = m.group(2) == "yes"
    return out


def _probe(addon: str) -> bool:
    try:
        return bool(PROBES[addon]())
    except Exception:  # Zustandsprüfung darf die Liste nie sprengen
        logger.warning("Zustandsprüfung für %s fehlgeschlagen", addon, exc_info=True)
        return False


def list_addons(conf: Path) -> list[dict]:
    enabled = _enabled(conf)
    wsl = is_wsl()
    return [{
        "id": addon,
        "installed": _probe(addon),
        "enabled": enabled.get(f"HH_INSTALL_{addon.upper()}", False),
        "restarts_service": addon in RESTARTS_SERVICE,
        "requires": REQUIRES.get(addon, []),
        "hint": "wsl" if wsl and addon in WSL_LIMITED else None,
    } for addon in ADDONS]
