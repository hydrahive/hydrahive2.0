"""Fixture `jobs` für die Waisen-Tests: Reihe nur einreihen, im Test selbst abarbeiten (Spec archiv-system.md, 2b)."""
from __future__ import annotations

import pytest


@pytest.fixture
def jobs(monkeypatch):
    from hydrahive.archive import jobs as j
    monkeypatch.setattr(j, "_start_worker", lambda: None)
    j.reset_for_tests()
    yield j
    j.reset_for_tests()
