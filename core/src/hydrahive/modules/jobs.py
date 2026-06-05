"""Modul-Hintergrundjob-Supervisor.

Startet die via `ctx.register_job()` registrierten Jobs als überwachte
asyncio-Tasks (ein Task pro Job), isoliert Exceptions pro Tick und stoppt
sauber beim Shutdown. Folgt dem Zahnfee-Scheduler-Muster
(`zahnfee/scheduler.py`): Loop + Stop-Event + try/except + Start-Verzögerung.
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.modules.context import ModuleJob
from hydrahive.modules.registry import REGISTRY

logger = logging.getLogger(__name__)


async def _run_job(module_id: str, job: ModuleJob, stop: asyncio.Event) -> None:
    """Loop für einen einzelnen Job: Start-Delay, dann fn alle interval_seconds.

    Der Stop-Event unterbricht sowohl die Start-Verzögerung als auch das
    Intervall-Warten, damit der Shutdown nicht bis zum nächsten Tick blockiert.
    """
    delay = max(0.0, job.initial_delay_seconds)
    if delay > 0:
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass
    while not stop.is_set():
        try:
            await job.fn()
        except Exception as e:
            logger.warning(
                "Modul-Job %s.%s fehlgeschlagen: %s",
                module_id, job.name, e, exc_info=True,
            )
        try:
            await asyncio.wait_for(stop.wait(), timeout=job.interval_seconds)
        except asyncio.TimeoutError:
            pass


def collect_jobs() -> list[tuple[str, ModuleJob]]:
    """Alle Jobs geladener Module als (module_id, job)-Paare."""
    out: list[tuple[str, ModuleJob]] = []
    for loaded in REGISTRY.values():
        if loaded.loaded and loaded.ctx:
            mid = loaded.manifest.id if loaded.manifest else loaded.name
            for job in loaded.ctx.jobs:
                out.append((mid, job))
    return out


def start_all(stop: asyncio.Event) -> list[asyncio.Task]:
    """Startet je einen überwachten Task pro registriertem Modul-Job."""
    tasks: list[asyncio.Task] = []
    for module_id, job in collect_jobs():
        tasks.append(asyncio.create_task(
            _run_job(module_id, job, stop),
            name=f"modjob-{module_id}-{job.name}",
        ))
        logger.info(
            "Modul-Job gestartet: %s.%s (alle %ss)",
            module_id, job.name, job.interval_seconds,
        )
    return tasks
