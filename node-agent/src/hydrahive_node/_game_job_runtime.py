"""Cancellation-aware execution loop for verified Game Studio jobs."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from hydrahive_node import jobs
from hydrahive_node.job_state import (
    mark_game_cancel_requested,
    mark_game_cancelled_pending_confirmation,
    save_job_result,
)
from hydrahive_node.storage import StatePaths

Exchange = Callable[[str, dict[str, object]], Awaitable[dict]]
Handler = Callable[[jobs.VerifiedOffer], Awaitable[dict[str, object]]]


async def _stop(execution: asyncio.Task) -> None:
    execution.cancel()
    try:
        await execution
    except asyncio.CancelledError:
        pass


async def execute_game_with_control(
    paths: StatePaths,
    job: jobs.VerifiedGameJob,
    exchange: Exchange,
    handler: Handler,
    public_key: str,
    *,
    control_poll_seconds: float,
    lease_renew_seconds: float,
) -> dict[str, object]:
    execution = asyncio.create_task(jobs.execute_offer(paths, job, handler))
    loop = asyncio.get_running_loop()
    next_renewal = loop.time() + lease_renew_seconds
    while True:
        done, _ = await asyncio.wait({execution}, timeout=control_poll_seconds)
        if done:
            return await execution
        try:
            control = await exchange("job_control_poll", {})
            if control.get("type") == "job_cancel":
                jobs.verify_cancel_message(
                    control,
                    public_key,
                    expected_node_id=job.node_id,
                    expected_job_id=job.job_id,
                    expected_lease_id=job.lease_id,
                )
                mark_game_cancel_requested(paths, job.idempotency_key)
                await _stop(execution)
                outcome: dict[str, object] = {
                    "type": "job_cancelled",
                    "job_id": job.job_id,
                    "lease_id": job.lease_id,
                }
                save_job_result(paths, job.idempotency_key, outcome)
                mark_game_cancelled_pending_confirmation(paths, job.idempotency_key)
                return outcome
            if control.get("type") != "no_control":
                raise RuntimeError("game control response is invalid")
            if loop.time() >= next_renewal:
                renewed = await exchange("job_renew", {"job_id": job.job_id, "lease_id": job.lease_id})
                if renewed.get("type") != "ack":
                    raise RuntimeError("game job lease was rejected")
                next_renewal = loop.time() + lease_renew_seconds
        except BaseException:
            await _stop(execution)
            raise
