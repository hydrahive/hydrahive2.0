"""Vorschlag für die eigene Kopplungs-Adresse (docs/specs/server-peering.md).

Die Gegenseite erreicht ``/api/peering/`` nur über das Tailnet (nginx erlaubt
nur 100.64.0.0/10 und die Tailscale-IPv6). Eine LAN-Adresse im Kopplungscode
führt still zu 403 – deshalb schlagen wir die Tailscale-IPv4 vor.
"""
from __future__ import annotations

import ipaddress
import re

_TAILNET_V4 = ipaddress.ip_network("100.64.0.0/10")
_FALLBACK_NAME = "hydrahive"


def _tailnet_ipv4(ip: object) -> str | None:
    if not isinstance(ip, str):
        return None
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None
    return ip if addr.version == 4 and addr in _TAILNET_V4 else None


def _safe_name(hostname: object) -> str:
    """Muss zum Namensmuster von OwnCodeRequest passen: ^[A-Za-z0-9._-]+$, ≤ 64."""
    raw = hostname if isinstance(hostname, str) else ""
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("-.")[:64]
    return name or _FALLBACK_NAME


def suggest_from_tailscale(status: dict) -> dict | None:
    """{name, url} aus dem Tailscale-Status – oder None, wenn nicht verbunden."""
    if not status.get("connected"):
        return None
    ip = _tailnet_ipv4(status.get("ip"))
    if not ip:
        return None
    return {"name": _safe_name(status.get("hostname")), "url": f"https://{ip}"}
