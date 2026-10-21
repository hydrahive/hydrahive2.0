"""Portfreigaben auf dem Mac: TCP-Weiterleitung Mac → Colima-VM (Plan docs/plans/mac-containers.md §4, Weg A).

Unter Linux lauscht das Incus-proxy-device direkt auf der WAN-/Tailscale-Adresse des Servers. Auf dem Mac läuft
Incus in einer Linux-VM; die Adressen gehören dem Mac. Darum lauscht das proxy device in der VM auf allen
VM-Adressen, und dieser Weiterleiter nimmt Verbindungen am Mac an (gewählte Adresse, Port ≥ 1024, kein root) und
reicht sie an die VM weiter. Nur TCP. Im Container erscheint als Absender die VM, nicht der echte Client.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time

logger = logging.getLogger(__name__)

# Installer-Ort der Container-Werkzeuge auf dem Mac (installer/modules-mac/70-containers.sh).
TOOLS_BIN = "/usr/local/lib/hydrahive2/containers/bin"
PROFILE = "hydrahive"
_VM_TTL_S = 30.0
_VM_CACHE: dict[str, tuple[float, str | None]] = {}
_BUF = 64 * 1024


def _colima() -> str | None:
    found = shutil.which("colima")
    if found:
        return found
    candidate = os.path.join(TOOLS_BIN, "colima")
    return candidate if os.path.isfile(candidate) and os.access(candidate, os.X_OK) else None


def vm_address() -> str | None:
    """Adresse der HydraHive-VM im Mac-Netz (`colima ls --json`), 30 s zwischengespeichert. None, wenn sie nicht läuft."""
    hit = _VM_CACHE.get(PROFILE)
    if hit and time.monotonic() - hit[0] < _VM_TTL_S:
        return hit[1]
    colima = _colima()
    addr: str | None = None
    if colima:
        try:
            out = subprocess.run([colima, "ls", "--json"], capture_output=True, text=True, timeout=10,
                                 env={**os.environ}).stdout
        except (OSError, subprocess.SubprocessError):
            out = ""
        for line in out.splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if item.get("name") == PROFILE and item.get("status") == "Running":
                addr = item.get("address") or None
    _VM_CACHE[PROFILE] = (time.monotonic(), addr)
    return addr


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await reader.read(_BUF):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.IncompleteReadError, OSError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


def _handler(target_host: str, target_port: int):
    async def handle(client_r: asyncio.StreamReader, client_w: asyncio.StreamWriter) -> None:
        try:
            up_r, up_w = await asyncio.wait_for(asyncio.open_connection(target_host, target_port), timeout=10)
        except (OSError, asyncio.TimeoutError):
            client_w.close()
            return
        await asyncio.gather(_pipe(client_r, up_w), _pipe(up_r, client_w))
    return handle


class Forwarder:
    """Offene Weiterleitungen je Freigabe-ID. open() ersetzt eine vorhandene, close() ist idempotent."""

    def __init__(self) -> None:
        self._servers: dict[str, list[asyncio.base_events.Server]] = {}

    def active(self) -> set[str]:
        return set(self._servers)

    async def open(self, rule_id: str, host: str, start: int, end: int, target_host: str, target_start: int) -> None:
        from hydrahive.containers.ports import PortError

        await self.close(rule_id)
        servers: list[asyncio.base_events.Server] = []
        try:
            for offset in range(end - start + 1):
                servers.append(await asyncio.start_server(
                    _handler(target_host, target_start + offset), host, start + offset))
        except OSError as exc:
            for srv in servers:
                srv.close()
            raise PortError("container_port_apply_failed", detail=f"Port belegt oder Adresse fehlt: {exc}") from exc
        self._servers[rule_id] = servers
        logger.info("Mac-Weiterleitung %s: %s:%s-%s → %s:%s", rule_id, host, start, end, target_host, target_start)

    async def close(self, rule_id: str) -> None:
        for srv in self._servers.pop(rule_id, []):
            srv.close()
            try:
                await asyncio.wait_for(srv.wait_closed(), timeout=2)
            except (asyncio.TimeoutError, Exception):
                pass

    async def close_all(self) -> None:
        for rule_id in list(self._servers):
            await self.close(rule_id)


FORWARDER = Forwarder()
