"""Polling and delivery loop for signed compute jobs."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import asdict

from hydrahive_node import jobs
from hydrahive_node.job_state import (
    load_delivered_jobs,
    load_job_executions,
    load_job_results,
    mark_job_result_delivered,
    prepare_job_execution,
    save_job_result,
)
from hydrahive_node.storage import AgentIdentity, StatePaths

Exchange = Callable[[str, dict[str, object]], Awaitable[dict]]
Handler = Callable[[jobs.VerifiedJob], Awaitable[dict[str, object]]]


async def _unsupported_handler(job: jobs.VerifiedJob) -> dict[str, object]:
    raise RuntimeError(f"operation is not installed: {job.operation}")


async def _deliver(exchange: Exchange, outcome: dict[str, object]) -> None:
    message_type = outcome.get("type")
    if message_type not in {"job_succeeded", "job_failed"}:
        raise RuntimeError("persisted job outcome is invalid")
    payload = {key: value for key, value in outcome.items() if key != "type"}
    response = await exchange(str(message_type), payload)
    if response.get("type") not in {"ack", "job_rejected"}:
        raise RuntimeError("job result was not acknowledged")


async def _flush_results(paths: StatePaths, exchange: Exchange) -> None:
    delivered = load_delivered_jobs(paths)
    for idempotency_key, outcome in load_job_results(paths).items():
        if idempotency_key in delivered:
            continue
        await _deliver(exchange, outcome)
        mark_job_result_delivered(paths, idempotency_key)


async def _execute_with_renewal(
    paths: StatePaths,
    job: jobs.VerifiedJob,
    exchange: Exchange,
    handler: Handler,
) -> dict[str, object]:
    execution = asyncio.create_task(jobs.execute_offer(paths, job, handler))
    while True:
        done, _ = await asyncio.wait({execution}, timeout=60.0)
        if done:
            return await execution
        try:
            response = await exchange("job_renew", {"job_id": job.job_id, "lease_id": job.lease_id})
        except BaseException:
            execution.cancel()
            try:
                await execution
            except asyncio.CancelledError:
                pass
            raise
        if response.get("type") == "ack":
            continue
        execution.cancel()
        try:
            await execution
        except asyncio.CancelledError:
            pass
        outcome: dict[str, object] = {
            "type": "job_failed",
            "job_id": job.job_id,
            "lease_id": job.lease_id,
            "error_code": "lease_lost",
            "error_params": {},
        }
        save_job_result(paths, job.idempotency_key, outcome)
        return outcome


async def _resume_executions(paths: StatePaths, exchange: Exchange, handler: Handler) -> None:
    delivered = load_delivered_jobs(paths)
    for idempotency_key, execution in load_job_executions(paths).items():
        if idempotency_key in delivered:
            mark_job_result_delivered(paths, idempotency_key)
            continue
        job_data = execution.get("job")
        if not isinstance(job_data, dict):
            raise RuntimeError("persisted job execution is invalid")
        job = jobs.VerifiedJob(**job_data)  # type: ignore[arg-type]
        if execution.get("state") == "accepted":
            started = await exchange("job_started", {"job_id": job.job_id, "lease_id": job.lease_id})
            if started.get("type") == "job_rejected":
                mark_job_result_delivered(paths, idempotency_key)
                continue
            if started.get("type") != "ack":
                raise RuntimeError("resumed job start was not acknowledged")
        elif execution.get("state") == "in_progress":
            renewed = await exchange("job_renew", {"job_id": job.job_id, "lease_id": job.lease_id})
            if renewed.get("type") == "job_rejected":
                mark_job_result_delivered(paths, idempotency_key)
                continue
            if renewed.get("type") != "ack":
                raise RuntimeError("resumed job lease was not acknowledged")
        outcome = await _execute_with_renewal(paths, job, exchange, handler)
        await _deliver(exchange, outcome)
        mark_job_result_delivered(paths, idempotency_key)


async def run_loop(
    paths: StatePaths,
    identity: AgentIdentity,
    exchange: Exchange,
    handler: Handler = _unsupported_handler,
) -> None:
    public_key = paths.job_signing_public_key.read_text(encoding="ascii").strip()
    await _flush_results(paths, exchange)
    await _resume_executions(paths, exchange, handler)
    while True:
        response = await exchange("job_poll", {})
        if response.get("type") == "no_job":
            await asyncio.sleep(2.0)
            continue
        verified = jobs.verify_offer(response, public_key, identity.node_id)
        prepare_job_execution(paths, asdict(verified))
        started = await exchange("job_started", {"job_id": verified.job_id, "lease_id": verified.lease_id})
        if started.get("type") == "job_rejected":
            mark_job_result_delivered(paths, verified.idempotency_key)
            continue
        if started.get("type") != "ack":
            raise RuntimeError("job start was not acknowledged")
        outcome = await _execute_with_renewal(paths, verified, exchange, handler)
        await _deliver(exchange, outcome)
        mark_job_result_delivered(paths, verified.idempotency_key)
