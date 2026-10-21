"""Portfreigaben auf dem Mac (docs/plans/mac-containers.md §4, Weg A).

Getrennt von ports.py, damit der Linux-Weg dort unverändert und übersichtlich bleibt. Alles über `ports.…`
aufgerufen – Tests ersetzen dort incus, Helfer und Markierung.
"""
from __future__ import annotations

import logging

from hydrahive.containers import mac_forward
from hydrahive.containers import ports

logger = logging.getLogger(__name__)


async def apply_mac(name: str, ipv4: str, rule: ports.PortRule) -> None:
    """Mac (docs/plans/mac-containers.md §4, Weg A): proxy device in der VM auf der VM-Adresse (nat=true verbietet 0.0.0.0), der Kern leitet von
    der LAN- bzw. Tailscale-Adresse des Macs an die VM weiter. Kein ufw, kein Root-Helfer. Nur TCP."""
    dev = ports._device(rule)
    try:
        await ports.incus.remove_device(name, dev)
        if rule.scope == "off":
            await mac_forward.FORWARDER.close(rule.id)
        else:
            if rule.protocol != "tcp":
                raise ports.PortError("container_port_apply_failed", detail="mac_udp_unsupported")
            addr = ports.nat.wan_ipv4() if rule.scope == "public" else await ports._tailscale_ipv4()
            vm = mac_forward.vm_address()
            if not addr or not vm:
                raise ports.PortError("container_port_apply_failed", detail=f"keine Adresse für {rule.scope}" if not addr
                                else "Container-VM nicht erreichbar")
            hosts = ports._range(rule.host_port_start, rule.host_port_end)
            cend = rule.container_port_start + (rule.host_port_end - rule.host_port_start)
            await ports.incus.add_proxy_device(
                name, dev, listen=f"tcp:{vm}:{hosts}",
                connect=f"tcp:{ipv4}:{ports._range(rule.container_port_start, cend)}",
            )
            await mac_forward.FORWARDER.open(rule.id, addr, rule.host_port_start, rule.host_port_end,
                                             vm, rule.host_port_start)
    except (ports.PortError, ports.incus.IncusError) as exc:
        detail = getattr(exc, "params", {}).get("detail") or getattr(exc, "params", {}).get("stderr") or exc.code
        ports._mark(rule.id, error=str(detail)[:300])
        logger.warning("Portfreigabe %s für %s fehlgeschlagen: %s", rule.id, name, detail)
        raise
    ports._mark(rule.id, error=None)
