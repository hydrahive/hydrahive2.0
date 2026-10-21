"""Read-only incus inspection functions (info, list, show_log, show_config, list_images)."""
from __future__ import annotations

import json

from hydrahive.containers import incus_client as _client


async def _run(*args: str, timeout: float = 60.0) -> tuple[int, str, str]:
    """Zur Laufzeit nachschlagen – so greifen Test-Fakes auf incus_client._run auch hier."""
    return await _client._run(*args, timeout=timeout)


async def info(name: str) -> dict | None:
    """Kompletter Status-Block via JSON."""
    rc, out, _ = await _run("query", f"/1.0/instances/{name}?recursion=1", timeout=20.0)
    if rc != 0:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


async def instance_exists(name: str) -> bool:
    """Gibt es in Incus schon eine Instanz dieses Namens (auch ohne HydraHive-Eintrag)?"""
    rc, _, _ = await _run("query", f"/1.0/instances/{name}", timeout=20.0)
    return rc == 0


async def nat_ips_in_use(network: str) -> set[str]:
    """Feste IPv4-Adressen, die Instanzen in Incus im Netz ``network`` belegen.

    Die IP-Vergabe (nat.allocate_ipv4) kennt nur die DB. Container, die es nur
    in Incus gibt, würden sonst dieselbe IP bekommen → „already defined on
    another NIC“ (Befund Mac 21.10.2026). Fehler → leere Menge.
    """
    rc, out, _ = await _run("query", "/1.0/instances?recursion=1", timeout=20.0)
    if rc != 0:
        return set()
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return set()
    if not isinstance(data, list):
        return set()
    used: set[str] = set()
    for inst in data:
        devices = inst.get("expanded_devices") or {} if isinstance(inst, dict) else {}
        for dev in devices.values():
            if isinstance(dev, dict) and dev.get("type") == "nic" \
                    and dev.get("network") == network and dev.get("ipv4.address"):
                used.add(dev["ipv4.address"])
    return used


async def list_running_names() -> set[str]:
    rc, out, _ = await _run("list", "--format=json", "--columns=ns", timeout=20.0)
    if rc != 0:
        return set()
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return set()
    return {i["name"] for i in data if i.get("status", "").lower() == "running"}


async def show_log(name: str) -> str:
    """Container-Lifecycle-Log via `incus info <name> --show-log`."""
    rc, out, err = await _run("info", name, "--show-log", timeout=15.0)
    if rc != 0:
        return err or "incus info failed"
    return out


async def show_config(name: str) -> str:
    """Container-Konfiguration als YAML via `incus config show <name>`."""
    rc, out, err = await _run("config", "show", name, timeout=15.0)
    if rc != 0:
        return err or "incus config show failed"
    return out


async def list_images(remote: str = "images") -> list[dict]:
    """Image-Catalog vom Remote."""
    rc, out, _ = await _run("image", "list", f"{remote}:", "--format=json", timeout=30.0)
    if rc != 0:
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return []
