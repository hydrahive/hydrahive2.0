"""incus-CLI-Wrapper.

Wir rufen `incus` als Subprocess auf — die REST-API über Unix-Socket wäre
sauberer, aber CLI ist robust und funktioniert mit jeder incus-Version.

Voraussetzungen:
- incus installiert + initialisiert (incus admin init --auto)
- Backend-User in der `incus-admin`-Gruppe ODER Service läuft als root
  (Production: hydrahive-User in Gruppe, gesetzt vom Installer)
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil

logger = logging.getLogger(__name__)


class IncusError(RuntimeError):
    def __init__(self, code: str, **params):
        super().__init__(f"{code}: {params}")
        self.code = code
        self.params = params


def is_available() -> bool:
    return shutil.which("incus") is not None


async def _run(*args: str, timeout: float = 60.0,
               input_bytes: bytes | None = None) -> tuple[int, str, str]:
    if not is_available():
        raise IncusError("incus_missing")
    try:
        proc = await asyncio.create_subprocess_exec(
            "incus", *args,
            stdin=asyncio.subprocess.PIPE if input_bytes else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        raise IncusError("incus_missing")
    try:
        out, err = await asyncio.wait_for(
            proc.communicate(input=input_bytes), timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise IncusError("incus_timeout")
    return proc.returncode or 0, out.decode(errors="replace"), err.decode(errors="replace")


async def launch(name: str, image: str, *,
                 network_mode: str = "bridged",
                 cpu: int | None = None,
                 ram_mb: int | None = None,
                 bridge: str = "br0",
                 privileged: bool = True) -> None:
    """Erzeugt + startet einen Container.

    privileged=True ist im nested-LXC-Setup Pflicht. Bare-Metal ginge auch
    unprivileged, aber das entscheidet der Installer global im default-Profil.
    """
    args = ["launch", image, name]
    if cpu:
        args += ["-c", f"limits.cpu={cpu}"]
    if ram_mb:
        args += ["-c", f"limits.memory={ram_mb}MiB"]
    if privileged:
        args += ["-c", "security.privileged=true", "-c", "security.nesting=true"]

    rc, _, err = await _run(*args, timeout=300.0)
    if rc != 0:
        raise IncusError("incus_launch_failed", stderr=err[:400])

    # Network-Device: bridged → eigene NIC auf br0 statt incusbr0
    if network_mode == "bridged":
        rc, _, err = await _run(
            "config", "device", "override", name, "eth0",
            f"parent={bridge}", "nictype=bridged",
            timeout=30.0,
        )
        if rc != 0:
            # Override scheitert wenn eth0 noch nicht da ist (sollte aber sein) —
            # alternativ neu hinzufügen
            await _run(
                "config", "device", "add", name, "eth0",
                "nic", "nictype=bridged", f"parent={bridge}",
                timeout=30.0,
            )
        # Restart damit das Override greift
        await _run("restart", name, timeout=60.0)
    elif network_mode == "isolated":
        await _run("config", "device", "remove", name, "eth0", timeout=30.0)


async def stop(name: str, *, force: bool = False) -> None:
    args = ["stop", name]
    if force:
        args.append("--force")
    rc, _, err = await _run(*args, timeout=60.0)
    if rc != 0 and "is not running" not in err.lower():
        raise IncusError("incus_stop_failed", stderr=err[:400])


async def start(name: str) -> None:
    rc, _, err = await _run("start", name, timeout=60.0)
    if rc != 0 and "already running" not in err.lower():
        raise IncusError("incus_start_failed", stderr=err[:400])


async def restart_(name: str) -> None:
    rc, _, err = await _run("restart", name, timeout=60.0)
    if rc != 0:
        raise IncusError("incus_restart_failed", stderr=err[:400])


async def delete(name: str, *, force: bool = True) -> None:
    args = ["delete", name]
    if force:
        args.append("--force")
    rc, _, err = await _run(*args, timeout=60.0)
    if rc != 0 and "not found" not in err.lower():
        raise IncusError("incus_delete_failed", stderr=err[:400])


async def info(name: str) -> dict | None:
    """Kompletter Status-Block via JSON."""
    rc, out, _ = await _run("query", f"/1.0/instances/{name}?recursion=1", timeout=20.0)
    if rc != 0:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


async def list_running_names() -> set[str]:
    rc, out, _ = await _run("list", "--format=json", "--columns=ns", timeout=20.0)
    if rc != 0:
        return set()
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return set()
    return {i["name"] for i in data if i.get("status", "").lower() == "running"}


async def list_images(remote: str = "images") -> list[dict]:
    """Image-Catalog vom Remote."""
    rc, out, _ = await _run("image", "list", f"{remote}:", "--format=json", timeout=30.0)
    if rc != 0:
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return []
