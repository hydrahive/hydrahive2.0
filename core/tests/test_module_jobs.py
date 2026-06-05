"""F1 — Modul-Hintergrundjobs: ctx.register_job + Supervisor.

Der Supervisor startet je Job einen überwachten asyncio-Task, isoliert
Exceptions pro Tick (ein kaputter Job bricht weder andere noch den Core)
und stoppt sauber per Stop-Event.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.modules import jobs as module_jobs
from hydrahive.modules.context import ModuleContext, ModuleJob
from hydrahive.modules.manifest import ModuleManifest
from hydrahive.modules.registry import LoadedModule


def test_register_job_speichert_job():
    ctx = ModuleContext("demo")

    async def f() -> None: ...

    ctx.register_job("poll", f, interval_seconds=60)
    assert len(ctx.jobs) == 1
    j = ctx.jobs[0]
    assert j.name == "poll"
    assert j.interval_seconds == 60
    assert j.fn is f


def test_register_job_lehnt_nichtpositives_intervall_ab():
    ctx = ModuleContext("demo")

    async def f() -> None: ...

    with pytest.raises(ValueError):
        ctx.register_job("poll", f, interval_seconds=0)


@pytest.mark.asyncio
async def test_run_job_laeuft_bis_stop():
    calls = 0

    async def f() -> None:
        nonlocal calls
        calls += 1

    job = ModuleJob(name="t", fn=f, interval_seconds=0.01, initial_delay_seconds=0.0)
    stop = asyncio.Event()
    task = asyncio.create_task(module_jobs._run_job("demo", job, stop))
    await asyncio.sleep(0.05)
    stop.set()
    await asyncio.wait_for(task, timeout=1.0)
    assert calls >= 2  # lief mehrfach


@pytest.mark.asyncio
async def test_run_job_isoliert_exceptions():
    calls = 0

    async def f() -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("boom")

    job = ModuleJob(name="t", fn=f, interval_seconds=0.01, initial_delay_seconds=0.0)
    stop = asyncio.Event()
    task = asyncio.create_task(module_jobs._run_job("demo", job, stop))
    await asyncio.sleep(0.05)
    stop.set()
    await asyncio.wait_for(task, timeout=1.0)
    assert calls >= 2  # Loop lief trotz Exception jedes Mal weiter


@pytest.mark.asyncio
async def test_run_job_stop_bricht_initial_delay_ab():
    """Stop während der Start-Verzögerung beendet den Job sofort (kein fn-Call)."""
    calls = 0

    async def f() -> None:
        nonlocal calls
        calls += 1

    job = ModuleJob(name="t", fn=f, interval_seconds=10, initial_delay_seconds=10)
    stop = asyncio.Event()
    task = asyncio.create_task(module_jobs._run_job("demo", job, stop))
    await asyncio.sleep(0.02)
    stop.set()
    await asyncio.wait_for(task, timeout=1.0)
    assert calls == 0  # Stop während Delay → fn nie aufgerufen


@pytest.mark.asyncio
async def test_start_all_und_stop_all(monkeypatch):
    calls = 0

    async def f() -> None:
        nonlocal calls
        calls += 1

    ctx = ModuleContext("demo")
    ctx.register_job("poll", f, interval_seconds=0.01, initial_delay_seconds=0.0)
    loaded = LoadedModule(
        name="demo",
        manifest=ModuleManifest(id="demo", name="Demo", version="1.0.0"),
        path=Path("."),
        ctx=ctx,
        loaded=True,
    )
    monkeypatch.setattr(module_jobs, "REGISTRY", {"demo": loaded})

    stop = asyncio.Event()
    tasks = module_jobs.start_all(stop)
    assert len(tasks) == 1
    await asyncio.sleep(0.05)
    await module_jobs.stop_all(stop, tasks, timeout=1.0)
    assert calls >= 2
    assert all(t.done() for t in tasks)


@pytest.mark.asyncio
async def test_collect_jobs_ueberspringt_nicht_geladene(monkeypatch):
    ctx = ModuleContext("ok")

    async def f() -> None: ...

    ctx.register_job("j", f, interval_seconds=5, initial_delay_seconds=0.0)
    good = LoadedModule(
        name="ok", manifest=ModuleManifest(id="ok", name="Ok", version="1.0.0"),
        path=Path("."), ctx=ctx, loaded=True,
    )
    broken = LoadedModule(
        name="broken", manifest=None, path=Path("."), ctx=None, loaded=False,
        error="kaputt",
    )
    monkeypatch.setattr(module_jobs, "REGISTRY", {"ok": good, "broken": broken})

    collected = module_jobs.collect_jobs()
    assert [mid for mid, _ in collected] == ["ok"]
