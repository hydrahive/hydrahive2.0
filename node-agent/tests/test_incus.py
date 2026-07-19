from __future__ import annotations

import asyncio
import json

import pytest

from hydrahive_node import incus
from hydrahive_node.jobs import VerifiedJob

RESOURCE_ID = "019f7be0-95fb-73d3-a87a-2290c85ea427"


def _job(operation: str, payload: dict[str, object], *, resource_id: str = RESOURCE_ID) -> VerifiedJob:
    return VerifiedJob(
        job_id="job-id",
        node_id="node-one",
        resource_kind="container",
        resource_id=resource_id,
        operation=operation,
        generation=1,
        payload=payload,
        idempotency_key=f"{operation}:1",
        lease_id="lease-id",
        lease_until="2099-01-01T00:00:00Z",
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "--project=evil", "image": "images:debian/12", "network_mode": "bridged"},
        {"name": "demo", "image": "--target=evil", "network_mode": "bridged"},
        {"name": "demo", "image": "images:debian/12", "network_mode": "host"},
        {"name": "demo", "image": "images:debian/12", "network_mode": "bridged", "extra": "bad"},
    ],
)
def test_create_rejects_unsafe_or_unknown_payload_before_subprocess(monkeypatch, payload) -> None:
    async def forbidden(*args, **kwargs):
        pytest.fail("invalid payload reached incus subprocess")

    monkeypatch.setattr(incus, "_run", forbidden)
    with pytest.raises(incus.IncusJobError):
        asyncio.run(incus.execute(_job("container.create", payload)))


def test_create_uses_fixed_argv_and_is_idempotent_for_owned_instance(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []
    status: str | None = None
    network: dict[str, str] = {}

    async def fake_run(*args: str, timeout: float = 60.0):
        nonlocal status
        calls.append(args)
        if args[0] == "list":
            instances = [{"name": "demo", "status": status}] if status is not None else []
            return (0, json.dumps(instances), "")
        if args[:2] == ("config", "get"):
            return (0, f"{RESOURCE_ID}\n", "")
        if args[:3] == ("config", "device", "override"):
            network.update(item.split("=", 1) for item in args[5:])
        if args[:2] == ("config", "show"):
            return (0, json.dumps({"devices": {"eth0": network}}), "")
        if args[0] == "init":
            status = "Stopped"
        elif args[0] == "start":
            status = "Running"
        return (0, "", "")

    monkeypatch.setattr(incus, "_run", fake_run)
    result = asyncio.run(
        incus.execute(
            _job(
                "container.create",
                {
                    "name": "demo",
                    "image": "images:debian/12",
                    "network_mode": "isolated",
                    "cpu": 2,
                    "ram_mb": 512,
                },
            )
        )
    )

    launch = next(call for call in calls if call[0] == "init")
    assert launch[-3:] == ("--", "images:debian/12", "demo")
    assert "user.hydrahive.id=019f7be0-95fb-73d3-a87a-2290c85ea427" in launch
    assert not any("security.privileged" in arg or "security.nesting" in arg for arg in launch)
    assert next(i for i, call in enumerate(calls) if call[0] == "init") < next(
        i for i, call in enumerate(calls) if call[:3] == ("config", "device", "override")
    )
    assert next(i for i, call in enumerate(calls) if call[:3] == ("config", "device", "override")) < next(
        i for i, call in enumerate(calls) if call[0] == "start"
    )
    assert any("type=none" in call for call in calls)
    assert result == {"actual_state": "running", "runtime_ref": "demo"}

    calls.clear()
    existing_network: dict[str, str] = {}

    async def existing(*args: str, timeout: float = 60.0):
        calls.append(args)
        if args[0] == "list":
            return (0, json.dumps([{"name": "demo", "status": "Running"}]), "")
        if args[:2] == ("config", "get"):
            return (0, f"{RESOURCE_ID}\n", "")
        if args[:3] == ("config", "device", "override"):
            existing_network.update(item.split("=", 1) for item in args[5:])
        if args[:2] == ("config", "show"):
            return (0, json.dumps({"devices": {"eth0": existing_network}}), "")
        return (0, "", "")

    monkeypatch.setattr(incus, "_run", existing)
    asyncio.run(
        incus.execute(
            _job(
                "container.create",
                {
                    "name": "demo",
                    "image": "images:debian/12",
                    "network_mode": "isolated",
                    "cpu": 2,
                    "ram_mb": 512,
                },
            )
        )
    )
    assert not any(call[0] == "init" for call in calls)
    mutations = len([call for call in calls if call[:2] == ("config", "device")])
    asyncio.run(
        incus.execute(
            _job(
                "container.create",
                {
                    "name": "demo",
                    "image": "images:debian/12",
                    "network_mode": "isolated",
                    "cpu": 2,
                    "ram_mb": 512,
                },
            )
        )
    )
    assert len([call for call in calls if call[:2] == ("config", "device")]) == mutations


def test_lifecycle_requires_matching_hydrahive_ownership(monkeypatch) -> None:
    async def foreign(*args: str, timeout: float = 60.0):
        if args[0] == "list":
            return (0, json.dumps([{"name": "demo", "status": "Running"}]), "")
        if args[:2] == ("config", "get"):
            return (0, "different-container\n", "")
        return (0, "", "")

    monkeypatch.setattr(incus, "_run", foreign)
    with pytest.raises(incus.IncusJobError, match="ownership"):
        asyncio.run(incus.execute(_job("container.delete", {"name": "demo"})))


def test_unknown_operation_fails_closed() -> None:
    with pytest.raises(incus.IncusJobError, match="operation"):
        asyncio.run(incus.execute(_job("container.shell", {"name": "demo"})))
