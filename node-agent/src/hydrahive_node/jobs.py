"""Signed job validation and crash-safe idempotent dispatch."""

from __future__ import annotations

import base64
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from hydrahive_node.job_state import (
    load_job_executions,
    load_job_results,
    mark_job_in_progress,
    save_job_result,
)
from hydrahive_node.storage import StatePaths

MAX_JOB_BYTES = 64 * 1024
ALLOWED_OPERATIONS = frozenset(
    {
        "container.create",
        "container.start",
        "container.stop",
        "container.restart",
        "container.delete",
        "container.inspect",
        "vm.create_from_image",
        "vm.start",
        "vm.stop",
        "vm.restart",
        "vm.delete",
        "vm.inspect",
    }
)
OFFER_FIELDS = {
    "job_id",
    "node_id",
    "resource_kind",
    "resource_id",
    "operation",
    "generation",
    "payload",
    "idempotency_key",
    "lease_id",
    "lease_until",
}


class JobValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class VerifiedJob:
    job_id: str
    node_id: str
    resource_kind: str
    resource_id: str | None
    operation: str
    generation: int
    payload: dict[str, object]
    idempotency_key: str
    lease_id: str
    lease_until: str


def canonical_offer(offer: dict) -> bytes:
    try:
        encoded = json.dumps(
            offer,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise JobValidationError("job offer contains invalid JSON") from exc
    if len(encoded) > MAX_JOB_BYTES:
        raise JobValidationError("job offer is too large")
    return encoded


def _decode(value: str) -> bytes:
    try:
        return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, TypeError) as exc:
        raise JobValidationError("job signature encoding is invalid") from exc


def verify_offer(message: dict, public_key: str, expected_node_id: str) -> VerifiedJob:
    if set(message) != {"type", "job", "signature"} or message.get("type") != "job_offer":
        raise JobValidationError("job offer envelope is invalid")
    offer = message.get("job")
    signature = message.get("signature")
    if not isinstance(offer, dict) or set(offer) != OFFER_FIELDS or not isinstance(signature, str):
        raise JobValidationError("job offer schema is invalid")
    try:
        key = Ed25519PublicKey.from_public_bytes(_decode(public_key))
        key.verify(_decode(signature), canonical_offer(offer))
    except (ValueError, InvalidSignature) as exc:
        raise JobValidationError("job signature is invalid") from exc
    if offer["node_id"] != expected_node_id:
        raise JobValidationError("job belongs to a different node")
    if offer["operation"] not in ALLOWED_OPERATIONS:
        raise JobValidationError("job operation is not allowed")
    if offer["resource_kind"] not in {"container", "vm"} or not str(offer["operation"]).startswith(
        f"{offer['resource_kind']}."
    ):
        raise JobValidationError("job resource kind is invalid")
    if not isinstance(offer["generation"], int) or offer["generation"] < 0 or not isinstance(offer["payload"], dict):
        raise JobValidationError("job payload is invalid")
    for field in ("job_id", "node_id", "idempotency_key", "lease_id", "lease_until"):
        if not isinstance(offer[field], str) or not 0 < len(offer[field]) <= 255:
            raise JobValidationError(f"job {field} is invalid")
    if offer["resource_id"] is not None and not isinstance(offer["resource_id"], str):
        raise JobValidationError("job resource_id is invalid")
    try:
        lease_until = datetime.fromisoformat(str(offer["lease_until"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise JobValidationError("job lease expiry is invalid") from exc
    if lease_until.tzinfo is None or lease_until.astimezone(UTC) <= datetime.now(UTC):
        raise JobValidationError("job lease has expired")
    return VerifiedJob(**offer)  # type: ignore[arg-type]


async def execute_offer(
    paths: StatePaths,
    job: VerifiedJob,
    handler: Callable[[VerifiedJob], Awaitable[dict[str, object]]],
) -> dict[str, object]:
    existing = load_job_results(paths).get(job.idempotency_key)
    if existing is not None:
        return existing
    execution = load_job_executions(paths).get(job.idempotency_key)
    if execution is None:
        raise RuntimeError("job execution was not durably prepared")
    if execution.get("state") == "in_progress":
        outcome: dict[str, object] = {
            "type": "job_failed",
            "job_id": job.job_id,
            "lease_id": job.lease_id,
            "error_code": "operation_outcome_unknown",
            "error_params": {},
        }
        save_job_result(paths, job.idempotency_key, outcome)
        return outcome
    mark_job_in_progress(paths, job.idempotency_key)
    try:
        result = await handler(job)
        if not isinstance(result, dict):
            raise TypeError("handler result must be an object")
        outcome = {
            "type": "job_succeeded",
            "job_id": job.job_id,
            "lease_id": job.lease_id,
            "result": result,
        }
    except Exception:
        outcome = {
            "type": "job_failed",
            "job_id": job.job_id,
            "lease_id": job.lease_id,
            "error_code": "operation_failed",
            "error_params": {},
        }
    if len(json.dumps(outcome, allow_nan=False).encode("utf-8")) > MAX_JOB_BYTES:
        outcome = {
            "type": "job_failed",
            "job_id": job.job_id,
            "lease_id": job.lease_id,
            "error_code": "result_too_large",
            "error_params": {},
        }
    save_job_result(paths, job.idempotency_key, outcome)
    return outcome
