"""Zahnfee läuft zur eingestellten ORTSZEIT (Task 8d2a29e5)."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from hydrahive.zahnfee.scheduler import is_run_hour


@pytest.fixture
def berlin(monkeypatch):
    monkeypatch.setenv("TZ", "Europe/Berlin")
    time.tzset()
    yield
    monkeypatch.delenv("TZ", raising=False)
    time.tzset()


def test_summer_three_oclock_local_is_one_utc(berlin):
    # 01.07.2026 01:30 UTC = 03:30 MESZ
    now = datetime(2026, 7, 1, 1, 30, tzinfo=timezone.utc)
    assert is_run_hour(3, now)
    assert not is_run_hour(1, now)


def test_winter_three_oclock_local_is_two_utc(berlin):
    now = datetime(2026, 1, 15, 2, 5, tzinfo=timezone.utc)  # 03:05 MEZ
    assert is_run_hour(3, now)
    assert not is_run_hour(2, now)
