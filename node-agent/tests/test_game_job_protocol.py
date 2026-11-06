from __future__ import annotations

import asyncio
import base64
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hydrahive_node import job_runtime, job_state, jobs, provider_dispatch
from hydrahive_node.storage import StatePaths

DIGEST = "sha256:" + "b" * 64
SOURCE = "a" * 40


def _key() -> tuple[Ed25519PrivateKey, str]:
    private = Ed25519PrivateKey.generate()
    public = base64.urlsafe_b64encode(
        private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ).decode("ascii").rstrip("=")
    return private, public


def _sign(private: Ed25519PrivateKey, body: dict) -> str:
    return base64.urlsafe_b64encode(private.sign(jobs.canonical_offer(body))).decode("ascii").rstrip("=")


def _game_offer(*, extra_request: dict | None = None, extra_offer: dict | None = None) -> tuple[dict, str, Ed25519PrivateKey]:
    private, public = _key()
    request = {
        "game_resource_id": "resource-a",
        "operation": "game.project.validate",
        "source_commit_sha": SOURCE,
        "source_snapshot_digest": None,
        "inventory_snapshot_id": "inventory-a",
        "engine": "godot",
        "engine_version": "4.5.1",
        "toolchain_digest": DIGEST,
        "profile_id": "debug-desktop",
        "input_revision": 1,
        "limits": {
            "timeout_seconds": 900,
            "cpu_cores": 4,
            "memory_mb": 8192,
            "disk_mb": 16384,
            "pids": 256,
            "network": "off",
        },
        "operation_payload": {"validation_profile_id": "validation-default"},
        "idempotency_key": "game-request-a",
    }
    request.update(extra_request or {})
    body = {
        "job_id": "job-a",
        "node_id": "node-a",
        "resource_kind": "game_workspace",
        "resource_id": "resource-a",
        "operation": "game.project.validate",
        "generation": 1,
        "payload": {
            "schema_version": 1,
            "workspace_handle": "workspace-a",
            "isolation_approval_id": "approval-a",
            "isolation_profile_id": "linux-microvm-v1",
            "runner_version": "1.0.0",
            "policy_digest": "sha256:policy-v1",
            "proof_digest": "sha256:proof-v1",
            "request": request,
        },
        "idempotency_key": "game-request-a",
        "lease_id": "lease-a",
        "lease_until": (datetime.now(UTC) + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "attempt_id": "lease-a",
        "provider": "game-runtime/v1",
        "project_id": "project-a",
        "game_resource_id": "resource-a",
        "workspace_generation": 1,
        "source_commit_sha": SOURCE,
        "source_snapshot_digest": None,
    }
    body.update(extra_offer or {})
    return {"type": "job_offer", "job": body, "signature": _sign(private, body)}, public, private


def _paths(tmp_path) -> StatePaths:
    paths = StatePaths(tmp_path / "state")
    paths.directory.mkdir(mode=0o700)
    return paths


def test_game_offer_is_strict_signed_and_fully_bound() -> None:
    message, public, _ = _game_offer()
    message["sequence"] = 7
    verified = jobs.verify_offer(message, public, "node-a")

    assert isinstance(verified, jobs.VerifiedGameJob)
    assert verified.provider == "game-runtime/v1"
    assert verified.workspace_generation == verified.generation


@pytest.mark.parametrize("field", ["shell", "command", "host_path", "mounts", "env", "secrets"])
def test_game_offer_rejects_unknown_or_dangerous_fields_after_valid_signature(field: str) -> None:
    message, public, private = _game_offer()
    message["job"][field] = "forbidden"
    message["signature"] = _sign(private, message["job"])

    with pytest.raises(jobs.JobValidationError, match="schema"):
        jobs.verify_offer(message, public, "node-a")


def test_game_offer_rejects_nested_unknown_field_and_binding_mismatch() -> None:
    message, public, private = _game_offer(extra_request={"command": "godot --headless"})
    message["signature"] = _sign(private, message["job"])
    with pytest.raises(jobs.JobValidationError, match="schema"):
        jobs.verify_offer(message, public, "node-a")

    mismatch, public, _ = _game_offer(extra_offer={"workspace_generation": 2})
    with pytest.raises(jobs.JobValidationError, match="binding"):
        jobs.verify_offer(mismatch, public, "node-a")

    idempotency_mismatch, public, _ = _game_offer(extra_offer={"idempotency_key": "different-key"})
    with pytest.raises(jobs.JobValidationError, match="idempotency_key"):
        jobs.verify_offer(idempotency_mismatch, public, "node-a")


def test_game_offer_rejects_tampering_wrong_node_and_non_strict_generation() -> None:
    message, public, _ = _game_offer()
    message["job"]["project_id"] = "project-b"
    with pytest.raises(jobs.JobValidationError, match="signature"):
        jobs.verify_offer(message, public, "node-a")

    wrong_node, public, _ = _game_offer()
    with pytest.raises(jobs.JobValidationError, match="node"):
        jobs.verify_offer(wrong_node, public, "node-b")

    boolean_generation, public, private = _game_offer(extra_offer={"generation": True, "workspace_generation": True})
    boolean_generation["signature"] = _sign(private, boolean_generation["job"])
    with pytest.raises(jobs.JobValidationError, match="generation"):
        jobs.verify_offer(boolean_generation, public, "node-a")


def test_signed_cancel_must_match_node_job_lease_and_deadline() -> None:
    private, public = _key()
    body = {
        "job_id": "job-a",
        "node_id": "node-a",
        "lease_id": "lease-a",
        "cancel_deadline": (datetime.now(UTC) + timedelta(seconds=30)).isoformat().replace("+00:00", "Z"),
    }
    message = {"type": "job_cancel", **body, "signature": _sign(private, body), "sequence": 9}

    verified = jobs.verify_cancel_message(
        message, public, expected_node_id="node-a", expected_job_id="job-a", expected_lease_id="lease-a"
    )
    assert verified.job_id == "job-a"

    message["lease_id"] = "lease-b"
    with pytest.raises(jobs.JobValidationError, match="signature"):
        jobs.verify_cancel_message(
            message, public, expected_node_id="node-a", expected_job_id="job-a", expected_lease_id="lease-a"
        )


def test_game_cancel_aborts_handler_persists_terminal_outcome_and_never_restarts(tmp_path, monkeypatch) -> None:
    paths = _paths(tmp_path)
    message, public, private = _game_offer()
    verified = jobs.verify_offer(message, public, "node-a")
    job_state.prepare_job_execution(paths, asdict(verified))
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def handler(job: jobs.VerifiedOffer) -> dict[str, object]:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    async def exchange(message_type: str, payload: dict[str, object]) -> dict:
        assert message_type == "job_control_poll"
        await started.wait()
        body = {
            "job_id": verified.job_id,
            "node_id": verified.node_id,
            "lease_id": verified.lease_id,
            "cancel_deadline": (datetime.now(UTC) + timedelta(seconds=30)).isoformat().replace("+00:00", "Z"),
        }
        return {"type": "job_cancel", **body, "signature": _sign(private, body)}

    monkeypatch.setattr(job_runtime, "CONTROL_POLL_SECONDS", 0.001)
    outcome = asyncio.run(
        job_runtime._execute_with_renewal(paths, verified, exchange, handler, public_key=public)
    )

    assert stopped.is_set()
    assert outcome == {"type": "job_cancelled", "job_id": "job-a", "lease_id": "lease-a"}
    execution = job_state.load_job_executions(paths)[verified.idempotency_key]
    assert execution["state"] == "cancelled_pending_confirmation"

    calls = 0

    async def must_not_restart(job: jobs.VerifiedOffer) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {}

    delivered: list[str] = []

    async def ack(message_type: str, payload: dict[str, object]) -> dict:
        delivered.append(message_type)
        return {"type": "ack"}

    asyncio.run(job_runtime._flush_results(paths, ack))
    asyncio.run(job_runtime._resume_executions(paths, ack, must_not_restart, public_key=public))
    assert delivered == ["job_cancelled"]
    assert calls == 0


def test_provider_dispatch_never_falls_back_to_host_or_legacy_incus_for_game_job() -> None:
    message, public, _ = _game_offer()
    verified = jobs.verify_offer(message, public, "node-a")

    with pytest.raises(provider_dispatch.ProviderDispatchError, match="not installed"):
        asyncio.run(provider_dispatch.execute(verified))
