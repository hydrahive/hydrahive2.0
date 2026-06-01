"""PG-Mirror-Backfill darf einen Start-Fehler nicht still verschlucken (#201).

Das frühere `except RuntimeError: pass` ließ einen nie startenden Backfill
unsichtbar — erklärt die offene Datamining-Backfill-Lücke. Jetzt wird der Fehler
geloggt statt geschluckt.
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.db import mirror


def test_start_backfill_logs_when_no_running_loop(monkeypatch, caplog):
    def _raise():
        raise RuntimeError("no running event loop")

    monkeypatch.setattr(mirror.asyncio, "get_running_loop", _raise)
    with caplog.at_level(logging.ERROR):
        mirror._start_backfill("some-model")  # darf NICHT werfen

    assert any("Backfill" in r.message for r in caplog.records), \
        "Start-Fehler muss geloggt werden, nicht still verschluckt"


def test_start_backfill_schedules_task_with_running_loop(monkeypatch):
    async def _noop(model, batch_size=100):
        return None

    monkeypatch.setattr(mirror, "_run_backfill", _noop)

    async def body():
        mirror._start_backfill("m")
        task = mirror._backfill_task
        assert task is not None
        await task  # sauber abwarten
        return True

    assert asyncio.run(body()) is True
