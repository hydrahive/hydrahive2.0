"""Crash-safe, idempotent execution of verified compute-job offers."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Protocol

from hydrahive_node.job_state import (
    load_job_executions,
    load_job_results,
    mark_job_in_progress,
    save_job_result,
)
from hydrahive_node.storage import StatePaths

MAX_JOB_BYTES = 64 * 1024
_RECONCILABLE_OPERATIONS = frozenset(
    {
        "container.create",
        "container.start",
        "container.stop",
        "container.delete",
        "container.inspect",
        "vm.create_from_image",
        "vm.start",
        "vm.stop",
        "vm.delete",
        "vm.inspect",
    }
)


class ExecutableJob(Protocol):
    job_id: str
    operation: str
    idempotency_key: str
    lease_id: str


async def execute_offer(
    paths: StatePaths,
    job: ExecutableJob,
    handler: Callable[[ExecutableJob], Awaitable[dict[str, object]]],
) -> dict[str, object]:
    existing = load_job_results(paths).get(job.idempotency_key)
    if existing is not None:
        return existing
    execution = load_job_executions(paths).get(job.idempotency_key)
    if execution is None:
        raise RuntimeError("job execution was not durably prepared")
    if execution.get("state") == "in_progress" and job.operation not in _RECONCILABLE_OPERATIONS:
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
    except Exception as exc:
        error_code = getattr(exc, "code", "operation_failed")
        if not isinstance(error_code, str) or not error_code.replace("_", "").isalnum() or len(error_code) > 128:
            error_code = "operation_failed"
        outcome = {
            "type": "job_failed",
            "job_id": job.job_id,
            "lease_id": job.lease_id,
            "error_code": error_code,
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
