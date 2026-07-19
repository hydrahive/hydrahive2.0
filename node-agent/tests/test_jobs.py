from __future__ import annotations

import asyncio
import base64
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hydrahive_node import jobs
from hydrahive_node.storage import StatePaths


def _signed_offer(*, node_id: str = "node-one", operation: str = "container.start") -> tuple[dict, str]:
    key = Ed25519PrivateKey.generate()
    public = (
        base64.urlsafe_b64encode(
            key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        )
        .decode("ascii")
        .rstrip("=")
    )
    payload = {
        "job_id": "job-one",
        "node_id": node_id,
        "resource_kind": "container",
        "resource_id": "demo",
        "operation": operation,
        "generation": 1,
        "payload": {"name": "demo"},
        "idempotency_key": "container:demo:start:1",
        "lease_id": "lease-one",
        "lease_until": (datetime.now(UTC) + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
    }
    signature = base64.urlsafe_b64encode(key.sign(jobs.canonical_offer(payload))).decode("ascii").rstrip("=")
    return {"type": "job_offer", "job": payload, "signature": signature}, public


def test_verify_offer_rejects_tampering_wrong_node_and_expiry() -> None:
    offer, public = _signed_offer()
    verified = jobs.verify_offer(offer, public, "node-one")
    assert verified.operation == "container.start"

    offer["job"]["operation"] = "container.delete"
    with pytest.raises(jobs.JobValidationError, match="signature"):
        jobs.verify_offer(offer, public, "node-one")

    fresh, public = _signed_offer(node_id="other")
    with pytest.raises(jobs.JobValidationError, match="node"):
        jobs.verify_offer(fresh, public, "node-one")


def test_dispatcher_persists_result_before_delivery_and_never_executes_twice(tmp_path) -> None:
    paths = StatePaths(tmp_path / "state")
    paths.directory.mkdir(mode=0o700)
    offer, public = _signed_offer()
    calls = 0

    async def handler(job: jobs.VerifiedJob) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"state": "running"}

    first = asyncio.run(jobs.execute_offer(paths, jobs.verify_offer(offer, public, "node-one"), handler))
    second = asyncio.run(jobs.execute_offer(paths, jobs.verify_offer(offer, public, "node-one"), handler))

    assert first == second
    assert first["type"] == "job_succeeded"
    assert calls == 1
    assert paths.job_results.stat().st_mode & 0o777 == 0o600
