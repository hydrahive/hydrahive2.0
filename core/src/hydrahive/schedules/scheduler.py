"""Persistent interval scheduler for direct Agent/Buddy tasks."""
from __future__ import annotations

import asyncio
import logging

from hydrahive.schedules import db
from hydrahive.schedules.execution import run_task

logger = logging.getLogger(__name__)
_TICK_SECONDS = 1.0
_MAX_CONCURRENT = 4


async def _run_claimed(task, run_id, semaphore: asyncio.Semaphore) -> None:
    async with semaphore:
        await run_task(task, run_id)


async def run_loop(stop: asyncio.Event) -> None:
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
    running: set[asyncio.Task] = set()
    try:
        while not stop.is_set():
            for task, run_id in db.claim_due():
                job = asyncio.create_task(_run_claimed(task, run_id, semaphore), name=f"scheduled-{task.task_id}")
                running.add(job)
                job.add_done_callback(running.discard)
            try:
                await asyncio.wait_for(stop.wait(), timeout=_TICK_SECONDS)
            except asyncio.TimeoutError:
                pass
    finally:
        if running:
            await asyncio.gather(*running, return_exceptions=True)


def request_run(task_id: str) -> bool:
    """Make a task due immediately; the normal loop performs the claim."""
    task = db.get(task_id)
    if not task or task.running:
        return False
    return db.make_due(task_id)
