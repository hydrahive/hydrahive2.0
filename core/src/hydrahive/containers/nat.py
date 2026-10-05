"""NAT-Netz für Container (docs/specs/container-nat-ports.md).

Auf Servern ohne br0 (VPS) hängen Container am incus-Netz ``hhnat0``
(10.10.0.0/24, angelegt vom Installer). Jeder NAT-Container bekommt eine
feste IP aus 10.10.0.10–10.10.0.199, damit Portfreigaben stabil bleiben.
Die DHCP-Range 10.10.0.200–250 bleibt für incus selbst.
"""
from __future__ import annotations

import ipaddress
import subprocess

from hydrahive.db.connection import db
from hydrahive.settings import settings

NAT_NETWORK = "hhnat0"
_SUBNET = ipaddress.ip_network("10.10.0.0/24")
_FIRST, _LAST = 10, 199


def bridge_available() -> bool:
    """br0 vorhanden? Dann gehen bridged Container."""
    return (_sys_net() / settings.vms_bridge).exists()


def nat_available() -> bool:
    """hhnat0 eingerichtet? incus legt dafür ein gleichnamiges Interface an."""
    return (_sys_net() / NAT_NETWORK).exists()


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


def wan_ipv4() -> str | None:
    """Öffentliche IPv4 des Servers (Quelle der Default-Route)."""
    try:
        out = subprocess.run(
            ["ip", "-4", "route", "get", "1.1.1.1"], capture_output=True, text=True, timeout=5,
        ).stdout.split()
        return out[out.index("src") + 1] if "src" in out else None
    except (OSError, subprocess.SubprocessError, IndexError):
        return None


def wan_interface() -> str | None:
    try:
        out = subprocess.run(
            ["ip", "-4", "route", "get", "1.1.1.1"], capture_output=True, text=True, timeout=5,
        ).stdout.split()
        return out[out.index("dev") + 1] if "dev" in out else None
    except (OSError, subprocess.SubprocessError, IndexError):
        return None
