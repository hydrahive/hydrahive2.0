"""Read-only incus inspection functions (info, list, show_log, show_config, list_images)."""
from __future__ import annotations

import json

from hydrahive.containers.incus_client import _run


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
