from __future__ import annotations

import asyncio
import json
import logging

from hydrahive.tailscale._bin import tailscale_bin

logger = logging.getLogger(__name__)
_AUTH_URL_PREFIX = "https://login.tailscale.com/"
# Laufende `tailscale up`-Prozesse (Anmeldung im Browser): eine Referenz halten, sonst räumt der GC sie weg.
_PENDING: set[asyncio.subprocess.Process] = set()


def _tailscale_bin() -> str:
    return tailscale_bin()


async def _run(*args: str, timeout: float = 30) -> str:
    proc = await asyncio.create_subprocess_exec(
        _tailscale_bin(), *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode().strip() or f"tailscale {args[0]} fehlgeschlagen")
    return stdout.decode().strip()


async def up(authkey: str, accept_routes: bool = False) -> None:
    # accept_routes default OFF: sonst werden Tailnet-Subnet/Exit-Routes auf
    # den Host gepusht und das LAN-Default-Interface verschwindet aus
    # `ip route get` — Server LAN-seitig unerreichbar. Opt-in only.
    args = ["up", f"--authkey={authkey}"]
    if accept_routes:
        args.append("--accept-routes")
    await _run(*args)


async def logout() -> None:
    await _run("logout", timeout=10)


async def login(timeout: float = 20) -> str | None:
    """Anmeldung ohne Auth-Key: `tailscale up --json` liefert als ersten JSON-Block den Anmelde-Link.

    Der Prozess läuft danach im Hintergrund weiter, bis die Anmeldung im Browser abgeschlossen ist (tailscaled
    wechselt dann auf „Running“). Rückgabe: der Link, oder None, wenn Tailscale schon verbunden ist.
    Nur Links auf login.tailscale.com werden weitergegeben (die Oberfläche öffnet sie).
    """
    proc = await asyncio.create_subprocess_exec(
        _tailscale_bin(), "up", "--json",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )

    async def first_block() -> dict:
        buf = ""
        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                raise RuntimeError("tailscale up beendet ohne Anmelde-Link")
            buf += line.decode(errors="replace")
            try:
                return json.loads(buf)
            except ValueError:
                continue

    try:
        block = await asyncio.wait_for(first_block(), timeout=timeout)
    except (asyncio.TimeoutError, RuntimeError) as exc:
        proc.kill()
        raise RuntimeError("Tailscale lieferte keinen Anmelde-Link") from exc
    if block.get("BackendState") == "Running" and not block.get("AuthURL"):
        return None
    url = str(block.get("AuthURL") or "")
    if not url.startswith(_AUTH_URL_PREFIX):
        proc.kill()
        raise RuntimeError("unerwarteter Anmelde-Link")
    _PENDING.add(proc)
    asyncio.get_running_loop().create_task(_reap(proc))
    return url


async def _reap(proc: asyncio.subprocess.Process) -> None:
    try:
        await proc.wait()
    finally:
        _PENDING.discard(proc)
