from __future__ import annotations

import asyncio
import json

import pytest

from hydrahive_node import incus


def _show(network: dict[str, str]) -> tuple[int, str, str]:
    return (0, json.dumps({"devices": {"eth0": network}}), "")


def test_network_configuration_uses_set_for_existing_local_device(monkeypatch) -> None:
    network = {"type": "nic", "nictype": "p2p"}
    actions: list[str] = []

    async def run(*args: str, timeout: float = 60.0):
        if args[:2] == ("config", "show"):
            return _show(network)
        action = args[2]
        actions.append(action)
        if action == "override":
            return (1, "", "already local")
        if action == "set":
            network.clear()
            network.update(item.split("=", 1) for item in args[5:])
            return (0, "", "")
        raise AssertionError("add must not run")

    monkeypatch.setattr(incus, "_run", run)
    asyncio.run(incus._configure_network("demo", "isolated"))
    assert actions == ["override", "set"]
    assert network == {"type": "none"}


def test_network_configuration_uses_add_when_device_is_missing(monkeypatch) -> None:
    network: dict[str, str] = {}
    actions: list[str] = []

    async def run(*args: str, timeout: float = 60.0):
        if args[:2] == ("config", "show"):
            return _show(network)
        action = args[2]
        actions.append(action)
        if action in {"override", "set"}:
            return (1, "", "missing")
        network.update({"type": args[5]})
        network.update(item.split("=", 1) for item in args[6:])
        return (0, "", "")

    monkeypatch.setattr(incus, "_run", run)
    asyncio.run(incus._configure_network("demo", "bridged"))
    assert actions == ["override", "set", "add"]
    assert network == {"type": "nic", "nictype": "bridged", "parent": "br0"}


def test_network_timeout_is_reconciled_against_expanded_config(monkeypatch) -> None:
    network = {"type": "nic"}
    calls = 0

    async def run(*args: str, timeout: float = 60.0):
        nonlocal calls
        if args[:2] == ("config", "show"):
            return _show(network)
        calls += 1
        network.clear()
        network.update({"type": "none"})
        raise TimeoutError

    monkeypatch.setattr(incus, "_run", run)
    asyncio.run(incus._configure_network("demo", "isolated"))
    assert calls == 1


def test_network_configuration_fails_if_postcondition_is_not_met(monkeypatch) -> None:
    async def run(*args: str, timeout: float = 60.0):
        if args[:2] == ("config", "show"):
            return _show({"type": "nic", "nictype": "p2p"})
        return (0, "", "")

    monkeypatch.setattr(incus, "_run", run)
    with pytest.raises(incus.IncusJobError, match="operation_failed"):
        asyncio.run(incus._configure_network("demo", "isolated"))
