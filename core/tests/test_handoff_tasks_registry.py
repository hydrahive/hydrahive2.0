"""Registry laufender Handoff-Tasks für den Graceful Shutdown (Spec
delegation-reliability.md 3.1) — macht asyncio.create_task(handoff_receiver.handle(...))
beim Server-Stopp gezielt abwartbar statt sie einfach abzuschneiden."""
from __future__ import annotations

import asyncio

from hydrahive.runner import handoff_tasks


def test_register_und_active_count():
    handoff_tasks.clear_for_test()

    async def _noop():
        await asyncio.sleep(0.2)

    async def go():
        task = asyncio.create_task(_noop())
        handoff_tasks.register("h1", task)
        assert handoff_tasks.active_count() == 1
        await task
        assert handoff_tasks.active_count() == 0

    asyncio.run(go())


def test_shutdown_cancelt_und_wartet_auf_laufende_tasks():
    handoff_tasks.clear_for_test()
    cleanup_ran: list[str] = []

    async def _work():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cleanup_ran.append("h1")
            raise

    async def go():
        task = asyncio.create_task(_work())
        handoff_tasks.register("h1", task)
        await asyncio.sleep(0)  # Task einmal anlaufen lassen, bevor gecancelt wird
        await handoff_tasks.shutdown(timeout=2.0)
        assert cleanup_ran == ["h1"]
        assert handoff_tasks.active_count() == 0

    asyncio.run(go())


def test_shutdown_ohne_laufende_tasks_ist_sofort_fertig():
    handoff_tasks.clear_for_test()
    asyncio.run(handoff_tasks.shutdown(timeout=1.0))
