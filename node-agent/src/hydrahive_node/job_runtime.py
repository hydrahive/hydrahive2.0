"""Polling and delivery loop for signed compute jobs."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from hydrahive_node import jobs
from hydrahive_node.job_state import load_delivered_jobs, load_job_results, mark_job_result_delivered
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
    if response.get("type") != "ack":
        raise RuntimeError("job result was not acknowledged")


async def _flush_results(paths: StatePaths, exchange: Exchange) -> None:
    delivered = load_delivered_jobs(paths)
    for idempotency_key, outcome in load_job_results(paths).items():
        if idempotency_key in delivered:
            continue
        await _deliver(exchange, outcome)
        mark_job_result_delivered(paths, idempotency_key)


async def run_loop(
    paths: StatePaths,
    identity: AgentIdentity,
    exchange: Exchange,
    handler: Handler = _unsupported_handler,
) -> None:
    public_key = paths.job_signing_public_key.read_text(encoding="ascii").strip()
    while True:
        await _flush_results(paths, exchange)
        response = await exchange("job_poll", {})
        if response.get("type") == "no_job":
            await asyncio.sleep(2.0)
            continue
        verified = jobs.verify_offer(response, public_key, identity.node_id)
        started = await exchange("job_started", {"job_id": verified.job_id, "lease_id": verified.lease_id})
        if started.get("type") != "ack":
            raise RuntimeError("job start was not acknowledged")
        outcome = await jobs.execute_offer(paths, verified, handler)
        await _deliver(exchange, outcome)
        mark_job_result_delivered(paths, verified.idempotency_key)
