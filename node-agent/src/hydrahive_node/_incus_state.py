"""Incus instance-state and ownership reconciliation helpers."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

from hydrahive_node._incus_validation import IncusJobError

Runner = Callable[..., Awaitable[tuple[int, str, str]]]


async def instance(run: Runner, name: str) -> dict | None:
    rc, output, _ = await run("list", name, "--format=json", timeout=20.0)
    if rc != 0:
        raise IncusJobError("incus_inspect_failed")
    try:
        instances = json.loads(output)
    except ValueError as exc:
        raise IncusJobError("incus_inspect_invalid") from exc
    if not isinstance(instances, list):
        raise IncusJobError("incus_inspect_invalid")
    exact = [item for item in instances if isinstance(item, dict) and item.get("name") == name]
    if len(exact) > 1:
        raise IncusJobError("incus_inspect_invalid")
    return exact[0] if exact else None


async def ownership(run: Runner, name: str, resource_id: str) -> dict | None:
    current = await instance(run, name)
    if current is None:
        return None
    rc, output, _ = await run("config", "get", name, "user.hydrahive.id", timeout=20.0)
    if rc != 0:
        raise IncusJobError("incus_inspect_failed")
    if not output.strip() or output.strip() != resource_id:
        raise IncusJobError("container_ownership_mismatch")
    return current


async def wait_for_owned(run: Runner, name: str, resource_id: str) -> dict | None:
    for _ in range(10):
        try:
            current = await ownership(run, name, resource_id)
        except IncusJobError as exc:
            if exc.code != "incus_inspect_failed":
                raise
            current = None
        if current is not None:
            return current
        await asyncio.sleep(0.5)
    return None


async def wait_for_state(run: Runner, name: str, resource_id: str, expected: str | None) -> bool:
    for _ in range(10):
        try:
            current = await ownership(run, name, resource_id)
        except IncusJobError as exc:
            if exc.code != "incus_inspect_failed":
                raise
            current = None
        if expected is None and current is None:
            return True
        if current is not None and str(current.get("status", "")).lower() == expected:
            return True
        await asyncio.sleep(0.5)
    return False
