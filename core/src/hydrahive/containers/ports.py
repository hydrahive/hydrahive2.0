"""Portfreigaben für NAT-Container (docs/specs/container-nat-ports.md).

Eine Freigabe = ein incus proxy device (nat=true, Kernel-DNAT, Client-IP
bleibt erhalten) + eine ufw-Route-Regel über den Root-Helfer
``hh-portforward``. Reichweite: public (öffentliche IP), tailnet
(Tailscale-IP), off (nur gespeichert, nichts aktiv).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass

from hydrahive.containers import incus_client as incus
from hydrahive.containers import nat
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

logger = logging.getLogger(__name__)

HELPER = "/usr/local/sbin/hh-portforward"
RESERVED = frozenset({22, 53, 80, 443, 3000, 3001, 5432, 6379, 8001, 8888, 9000, 9001, 10000, 41641})
MAX_RANGE = 100
PROTOCOLS = ("tcp", "udp")
SCOPES = ("public", "tailnet", "off")


class PortError(Exception):
    def __init__(self, code: str, **params) -> None:
        super().__init__(code)
        self.code = code
        self.params = params


@dataclass
class PortRule:
    id: str
    container_id: str
    protocol: str
    host_port_start: int
    host_port_end: int
    container_port_start: int
    scope: str
    label: str
    created_at: str
    applied_at: str | None = None
    last_error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _row(r) -> PortRule:
    return PortRule(**{k: r[k] for k in PortRule.__dataclass_fields__})


def list_for(container_id: str) -> list[PortRule]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM container_ports WHERE container_id = ? ORDER BY host_port_start",
            (container_id,),
        ).fetchall()
    return [_row(r) for r in rows]


def get(port_id: str) -> PortRule | None:
    with db() as conn:
        r = conn.execute("SELECT * FROM container_ports WHERE id = ?", (port_id,)).fetchone()
    return _row(r) if r else None


def validate(protocol: str, start: int, end: int, cstart: int, scope: str, *, exclude: str | None = None) -> None:
    if protocol not in PROTOCOLS:
        raise PortError("container_port_range_invalid")
    if scope not in SCOPES:
        raise PortError("container_port_range_invalid")
    if not (1024 <= start <= end <= 65535) or end - start >= MAX_RANGE:
        raise PortError("container_port_range_invalid")
    if not 1 <= cstart <= 65535 - (end - start):
        raise PortError("container_port_range_invalid")
    hit = next((p for p in range(start, end + 1) if p in RESERVED), None)
    if hit is not None:
        raise PortError("container_port_reserved", port=hit)
    with db() as conn:
        clash = conn.execute(
            "SELECT host_port_start, host_port_end FROM container_ports "
            "WHERE protocol = ? AND host_port_start <= ? AND host_port_end >= ? AND id != ?",
            (protocol, end, start, exclude or ""),
        ).fetchone()
    if clash:
        raise PortError("container_port_conflict", start=clash[0], end=clash[1])


def create(container_id: str, protocol: str, start: int, end: int, cstart: int, scope: str, label: str) -> PortRule:
    validate(protocol, start, end, cstart, scope)
    pid = uuid7()
    with db() as conn:
        conn.execute(
            "INSERT INTO container_ports (id, container_id, protocol, host_port_start, host_port_end, "
            "container_port_start, scope, label, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (pid, container_id, protocol, start, end, cstart, scope, label[:64], now_iso()),
        )
    return get(pid)  # type: ignore[return-value]


def set_scope(port_id: str, scope: str) -> PortRule | None:
    if scope not in SCOPES:
        raise PortError("container_port_range_invalid")
    with db() as conn:
        conn.execute("UPDATE container_ports SET scope = ? WHERE id = ?", (scope, port_id))
    return get(port_id)


def delete_row(port_id: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM container_ports WHERE id = ?", (port_id,))


def _mark(port_id: str, *, error: str | None) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE container_ports SET applied_at = ?, last_error = ? WHERE id = ?",
            (None if error else now_iso(), error, port_id),
        )


def _device(rule: PortRule) -> str:
    return f"hhp-{rule.id[-12:]}"


def _range(a: int, b: int) -> str:
    return str(a) if a == b else f"{a}-{b}"


async def _helper(*args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "sudo", "-n", HELPER, *args,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await asyncio.wait_for(proc.communicate(), timeout=60)
    if proc.returncode != 0:
        raise PortError("container_port_apply_failed", detail=err.decode(errors="replace")[:200])


async def apply(name: str, ipv4: str, rule: PortRule) -> None:
    """Setzt Proxy-Device + ufw passend zur Reichweite. Fehler landen in last_error."""
    dev = _device(rule)
    try:
        await incus.remove_device(name, dev)
        if rule.scope != "off":
            addr = nat.wan_ipv4() if rule.scope == "public" else await _tailscale_ipv4()
            if not addr:
                raise PortError("container_port_apply_failed", detail=f"keine Adresse für {rule.scope}")
            cend = rule.container_port_start + (rule.host_port_end - rule.host_port_start)
            await incus.add_proxy_device(
                name, dev,
                listen=f"{rule.protocol}:{addr}:{_range(rule.host_port_start, rule.host_port_end)}",
                connect=f"{rule.protocol}:{ipv4}:{_range(rule.container_port_start, cend)}",
            )
        await _helper(
            "apply", rule.id, rule.protocol, str(rule.host_port_start), str(rule.host_port_end),
            ipv4, str(rule.container_port_start), rule.scope, nat.wan_interface() or "eth0",
        )
    except (PortError, incus.IncusError) as exc:
        detail = getattr(exc, "params", {}).get("detail") or getattr(exc, "params", {}).get("stderr") or exc.code
        _mark(rule.id, error=str(detail)[:300])
        logger.warning("Portfreigabe %s für %s fehlgeschlagen: %s", rule.id, name, detail)
        raise
    _mark(rule.id, error=None)


async def remove(name: str, rule: PortRule) -> None:
    await incus.remove_device(name, _device(rule))
    await _helper("remove", rule.id)


async def _tailscale_ipv4() -> str | None:
    from hydrahive.tailscale.status import get_status
    try:
        return (await get_status()).get("ip")
    except Exception:
        return None
