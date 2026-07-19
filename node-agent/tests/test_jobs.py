from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hydrahive_node import job_runtime, job_state, jobs
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

    verified = jobs.verify_offer(offer, public, "node-one")
    job_state.prepare_job_execution(paths, asdict(verified))
    first = asyncio.run(jobs.execute_offer(paths, verified, handler))
    second = asyncio.run(jobs.execute_offer(paths, verified, handler))

    assert first == second
    assert first["type"] == "job_succeeded"
    assert calls == 1
    assert paths.job_results.stat().st_mode & 0o777 == 0o600


def test_interrupted_in_progress_job_is_not_executed_again(tmp_path) -> None:
    paths = StatePaths(tmp_path / "state")
    paths.directory.mkdir(mode=0o700)
    offer, public = _signed_offer()
    verified = jobs.verify_offer(offer, public, "node-one")
    job_state.prepare_job_execution(paths, asdict(verified))
    job_state.mark_job_in_progress(paths, verified.idempotency_key)
    calls = 0

    async def handler(job: jobs.VerifiedJob) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {}

    outcome = asyncio.run(jobs.execute_offer(paths, verified, handler))

    assert calls == 0
    assert outcome["error_code"] == "operation_outcome_unknown"


def test_delivered_job_state_is_bounded_and_pending_payload_is_removed(tmp_path, monkeypatch) -> None:
    paths = StatePaths(tmp_path / "state")
    paths.directory.mkdir(mode=0o700)
    monkeypatch.setattr(job_state, "MAX_STORED_JOBS", 2)
    job_state.save_job_result(paths, "one", {"type": "job_failed"})
    job_state.mark_job_result_delivered(paths, "one")
    job_state.mark_job_result_delivered(paths, "two")
    job_state.mark_job_result_delivered(paths, "three")

    assert job_state.load_job_results(paths) == {}
    assert job_state.load_delivered_jobs(paths) == {"two", "three"}


def test_resume_cleans_journal_if_delivery_marker_was_already_committed(tmp_path) -> None:
    paths = StatePaths(tmp_path / "state")
    paths.directory.mkdir(mode=0o700)
    offer, public = _signed_offer()
    verified = jobs.verify_offer(offer, public, "node-one")
    job_state.prepare_job_execution(paths, asdict(verified))
    job_state.mark_job_in_progress(paths, verified.idempotency_key)
    paths.delivered_jobs.write_text(json.dumps([verified.idempotency_key]), encoding="utf-8")

    async def unused_exchange(message_type: str, payload: dict[str, object]) -> dict:
        raise AssertionError("delivered job must not contact the control plane")

    async def unused_handler(job: jobs.VerifiedJob) -> dict[str, object]:
        raise AssertionError("delivered job must not execute")

    asyncio.run(job_runtime._resume_executions(paths, unused_exchange, unused_handler))
    assert job_state.load_job_executions(paths) == {}


def test_renewal_transport_failure_cancels_running_handler(tmp_path, monkeypatch) -> None:
    paths = StatePaths(tmp_path / "state")
    paths.directory.mkdir(mode=0o700)
    offer, public = _signed_offer()
    verified = jobs.verify_offer(offer, public, "node-one")
    job_state.prepare_job_execution(paths, asdict(verified))
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def handler(job: jobs.VerifiedJob) -> dict[str, object]:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    async def immediate_timeout(awaitables, timeout):
        await started.wait()
        return set(), set(awaitables)

    async def failed_exchange(message_type: str, payload: dict[str, object]) -> dict:
        raise ConnectionError("connection lost")

    monkeypatch.setattr(job_runtime.asyncio, "wait", immediate_timeout)
    with pytest.raises(ConnectionError, match="connection lost"):
        asyncio.run(job_runtime._execute_with_renewal(paths, verified, failed_exchange, handler))
    assert cancelled.is_set()
