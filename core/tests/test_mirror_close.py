"""Datamining-Spiegel beim Herunterfahren (Task a11e9091).

Prod 07.10.: Nach dem 20-s-Zeitlimit hing der Shutdown noch 18 s im Spiegel – pool.close() wartet auf alle
ausgeliehenen Verbindungen, laufende Schreib-/Embedding-Aufgaben wurden nicht abgebrochen, neue liefen gegen
einen schließenden Pool („pool is closing“).
"""
from __future__ import annotations

import asyncio
import time

import pytest

from hydrahive.db import _mirror_tasks, mirror


class _Pool:
    def __init__(self, close_hangs: bool = False):
        self.closed = self.terminated = False
        self._hang = close_hangs

    async def close(self):
        if self._hang:
            await asyncio.sleep(3600)
        self.closed = True

    def terminate(self):
        self.terminated = True


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(mirror, "_pool", None)
    monkeypatch.setattr(mirror, "_backfill_task", None)
    monkeypatch.setattr(_mirror_tasks, "closing", False)
    monkeypatch.setattr(_mirror_tasks, "tasks", set())
    monkeypatch.setattr(_mirror_tasks, "CLOSE_WAIT_S", 0.3)
    monkeypatch.setattr(_mirror_tasks, "POOL_CLOSE_S", 0.3)


def test_close_without_pool_is_noop():
    asyncio.run(mirror.close())
    assert mirror._pool is None


def test_close_cancels_hanging_tasks_and_closes_pool_quickly(monkeypatch):
    pool = _Pool()
    monkeypatch.setattr(mirror, "_pool", pool)

    async def body():
        hang = _mirror_tasks.track(asyncio.sleep(3600))
        quick = _mirror_tasks.track(asyncio.sleep(0.01))
        t0 = time.monotonic()
        await mirror.close()
        return time.monotonic() - t0, hang, quick

    took, hang, quick = asyncio.run(body())
    assert took < 1.5
    assert hang.cancelled() and quick.done() and not quick.cancelled()
    assert pool.closed and mirror._pool is None and not _mirror_tasks.tasks


def test_pool_close_that_hangs_is_terminated(monkeypatch):
    pool = _Pool(close_hangs=True)
    monkeypatch.setattr(mirror, "_pool", pool)
    t0 = time.monotonic()
    asyncio.run(mirror.close())
    assert time.monotonic() - t0 < 1.5 and pool.terminated and mirror._pool is None


def test_no_new_writes_after_close_started(monkeypatch):
    monkeypatch.setattr(mirror, "_pool", _Pool())
    started = []

    async def fake_write(pool, *a):
        started.append(a)
    monkeypatch.setattr(mirror, "write_message", fake_write)
    monkeypatch.setattr(mirror, "write_session", fake_write)

    async def body():
        _mirror_tasks.closing = True
        mirror.schedule_message(object(), object())
        mirror.schedule_session(object())
        await asyncio.sleep(0.05)
    asyncio.run(body())
    assert started == [] and not _mirror_tasks.tasks


def test_writes_are_tracked_and_removed_when_done(monkeypatch):
    monkeypatch.setattr(mirror, "_pool", _Pool())
    done = []

    async def fake_write(pool, *a):
        done.append(a)
    monkeypatch.setattr(mirror, "write_message", fake_write)

    async def body():
        mirror.schedule_message("m", "s")
        assert len(_mirror_tasks.tasks) == 1
        await asyncio.sleep(0.05)
        return len(_mirror_tasks.tasks)
    assert asyncio.run(body()) == 0 and done == [("m", "s")]


def test_close_cancels_running_backfill(monkeypatch):
    monkeypatch.setattr(mirror, "_pool", _Pool())

    async def body():
        mirror._backfill_task = asyncio.get_running_loop().create_task(asyncio.sleep(3600))
        task = mirror._backfill_task
        await mirror.close()
        return task
    assert asyncio.run(body()).cancelled()


def test_embeddings_are_tracked_and_stop_when_closing(monkeypatch):
    from hydrahive.db import _mirror_embed
    monkeypatch.setattr("hydrahive.llm._config.load_config", lambda: {"embed_model": "emb-model"})
    started = []

    async def fake_embed(pool, event_id, text, model):
        started.append(event_id)
        await asyncio.sleep(3600)
    monkeypatch.setattr(_mirror_embed, "embed_event", fake_embed)
    events = [{"id": "e1", "text": "Hallo"}, {"id": "e2", "text": "Welt"}]

    async def body():
        _mirror_embed.queue_embed(_Pool(), events)
        await asyncio.sleep(0.01)
        n = len(_mirror_tasks.tasks)
        cancelled = await _mirror_tasks.drain(0.05)
        _mirror_tasks.closing = True
        _mirror_embed.queue_embed(_Pool(), [{"id": "e3", "text": "später"}])
        await asyncio.sleep(0.01)
        return n, cancelled
    n, cancelled = asyncio.run(body())
    assert n == 2 and cancelled == 2 and started == ["e1", "e2"]
