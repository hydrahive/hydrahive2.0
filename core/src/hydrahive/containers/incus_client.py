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



def host_is_lxc() -> bool:
    """Läuft HydraHive selbst in einem LXC-Container (nested)?"""
    import subprocess
    try:
        out = subprocess.run(
            ["systemd-detect-virt", "--container"], capture_output=True, text=True, timeout=5, check=False,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return False
    return out == "lxc"

async def launch(name: str, image: str, *,
                 network_mode: str = "bridged",
                 cpu: int | None = None,
                 ram_mb: int | None = None,
                 bridge: str = "br0",
                 ipv4: str | None = None,
                 privileged: bool | None = None) -> None:
    """Erzeugt + startet einen Container.

    Standard ist UNPRIVILEGIERT (eigener UID-Bereich), aber mit
    security.nesting=true: Aktuelle systemd-Versionen (Ubuntu 26.04) hängen
    ohne nesting beim Booten. Privilegiert nur, wenn HydraHive selbst in einem
    LXC-Container läuft – dort Pflicht – oder auf ausdrücklichen Wunsch.

    Befund VPS 05.10.2026 (ubuntu/26.04, debian/12):
      privilegiert+nesting → läuft, "degraded" (netplan/udevadm)
      unprivilegiert ohne nesting → bootet nicht
      unprivilegiert+nesting → "running", Netz + DNS ok
    Früher war privileged=True für jeden Container gesetzt: ein Ausbruch aus
    einem öffentlich erreichbaren Container wäre root am Host gewesen.
    """
    if privileged is None:
        privileged = host_is_lxc()
    # Optionen zuerst, dann '--', dann die Positional-Args (image, name). Das '--'
    # garantiert, dass incus/cobra image/name NIE als Flags interpretiert, selbst
    # wenn der Wert mit '-' beginnt (Defense-in-Depth zur IMAGE_RE-Allowlist, #185).
    opts: list[str] = []
    if cpu:
        opts += ["-c", f"limits.cpu={cpu}"]
    if ram_mb:
        opts += ["-c", f"limits.memory={ram_mb}MiB"]
    opts += ["-c", "security.nesting=true"]
    if privileged:
        opts += ["-c", "security.privileged=true"]
    args = ["launch", *opts, "--", image, name]

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
    elif network_mode == "nat":
        # NAT-Netz hhnat0 mit fester IP (docs/specs/container-nat-ports.md).
        # Das default-Profil hat keine NIC; eth0 wird hier angelegt.
        from hydrahive.containers.nat import NAT_NETWORK
        if not ipv4:
            raise IncusError("container_nat_no_ip")
        rc, _, err = await _run(
            "config", "device", "add", name, "eth0", "nic",
            f"network={NAT_NETWORK}", f"ipv4.address={ipv4}",
            timeout=30.0,
        )
        if rc != 0:
            raise IncusError("incus_launch_failed", stderr=err[:400])
        await _run("restart", name, timeout=60.0)
    elif network_mode == "isolated":
        await _run("config", "device", "remove", name, "eth0", timeout=30.0)



async def add_proxy_device(name: str, device: str, *, listen: str, connect: str) -> None:
    """Portfreigabe per proxy device mit nat=true (Kernel-DNAT, Client-IP bleibt)."""
    rc, _, err = await _run(
        "config", "device", "add", name, device, "proxy",
        f"listen={listen}", f"connect={connect}", "nat=true",
        timeout=30.0,
    )
    if rc != 0:
        raise IncusError("incus_device_failed", stderr=err[:400])


async def remove_device(name: str, device: str) -> None:
    """Idempotent: fehlendes Device ist kein Fehler."""
    rc, _, err = await _run("config", "device", "remove", name, device, timeout=30.0)
    if rc != 0 and "not found" not in err.lower() and "doesn't exist" not in err.lower():
        raise IncusError("incus_device_failed", stderr=err[:400])

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


from hydrahive.containers._incus_inspect import (
    info, list_running_names, show_log, show_config, list_images,
)
