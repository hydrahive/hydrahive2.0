"""NAT-Netz für Container (docs/specs/container-nat-ports.md).

Auf Servern ohne br0 (VPS) hängen Container am incus-Netz ``hhnat0``
(10.10.0.0/24, angelegt vom Installer). Jeder NAT-Container bekommt eine
feste IP aus 10.10.0.10–10.10.0.199, damit Portfreigaben stabil bleiben.
Die DHCP-Range 10.10.0.200–250 bleibt für incus selbst.
"""
from __future__ import annotations

import ipaddress
import shutil
import subprocess

from hydrahive.containers import _platform
from hydrahive.db.connection import db
from hydrahive.settings import settings

NAT_NETWORK = "hhnat0"
_SUBNET = ipaddress.ip_network("10.10.0.0/24")
_FIRST, _LAST = 10, 199


def bridge_available() -> bool:
    """br0 vorhanden? Dann gehen bridged Container. Auf dem Mac nie (Incus in einer VM, keine Brücke ins LAN)."""
    if _platform.is_mac():
        return False
    return (_sys_net() / settings.vms_bridge).exists()


def nat_available() -> bool:
    """hhnat0 eingerichtet? Linux: incus legt ein gleichnamiges Interface an. Mac: Netz in der Colima-VM."""
    if _platform.is_mac():
        return _incus_network_exists(NAT_NETWORK)
    return (_sys_net() / NAT_NETWORK).exists()


def _incus_network_exists(name: str) -> bool:
    """Gibt es das Incus-Netz? Nur für den Mac – dort fehlt /sys/class/net."""
    incus = shutil.which("incus")
    if not incus:
        return False
    try:
        return subprocess.run([incus, "network", "show", name], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _sys_net():
    from pathlib import Path
    return Path("/sys/class/net")


def network_modes() -> dict:
    bridged, nat = bridge_available(), nat_available()
    default = "bridged" if bridged else ("nat" if nat else "isolated")
    return {"bridged": bridged, "nat": nat, "isolated": True, "default": default}


def allocate_ipv4() -> str:
    """Nächste freie feste IP. ValueError, wenn alle vergeben sind."""
    with db() as conn:
        used = {r[0] for r in conn.execute("SELECT ipv4 FROM containers WHERE ipv4 IS NOT NULL")}
    for host in range(_FIRST, _LAST + 1):
        ip = str(_SUBNET.network_address + host)
        if ip not in used:
            return ip
    raise ValueError("Keine freie IP im NAT-Netz")


def set_ipv4(container_id: str, ip: str | None) -> None:
    with db() as conn:
        conn.execute("UPDATE containers SET ipv4 = ? WHERE container_id = ?", (ip, container_id))


def get_ipv4(container_id: str) -> str | None:
    with db() as conn:
        row = conn.execute("SELECT ipv4 FROM containers WHERE container_id = ?", (container_id,)).fetchone()
    return row[0] if row else None


def _mac_default_interface() -> str | None:
    try:
        out = subprocess.run(["route", "-n", "get", "default"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in out.splitlines():
        key, _, value = line.strip().partition(":")
        if key == "interface" and value.strip():
            return value.strip()
    return None


def wan_ipv4() -> str | None:
    """Öffentliche IPv4 des Servers (Quelle der Default-Route). Mac: Adresse der Standard-Schnittstelle."""
    if _platform.is_mac():
        iface = _mac_default_interface()
        if not iface:
            return None
        try:
            out = subprocess.run(["ipconfig", "getifaddr", iface], capture_output=True, text=True, timeout=5).stdout
        except (OSError, subprocess.SubprocessError):
            return None
        return out.strip() or None
    try:
        out = subprocess.run(
            ["ip", "-4", "route", "get", "1.1.1.1"], capture_output=True, text=True, timeout=5,
        ).stdout.split()
        return out[out.index("src") + 1] if "src" in out else None
    except (OSError, subprocess.SubprocessError, IndexError):
        return None


def wan_interface() -> str | None:
    if _platform.is_mac():
        return _mac_default_interface()
    try:
        out = subprocess.run(
            ["ip", "-4", "route", "get", "1.1.1.1"], capture_output=True, text=True, timeout=5,
        ).stdout.split()
        return out[out.index("dev") + 1] if "dev" in out else None
    except (OSError, subprocess.SubprocessError, IndexError):
        return None
