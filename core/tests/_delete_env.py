"""Fixture `archive_root` für die Lösch-Tests (Spec archiv-system.md, Etappe 2).

Eingebunden per `pytest_plugins = ["tests._delete_env"]`; Hilfsfunktionen stehen in tests/_delete_fixtures.py.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def archive_root(tmp_path, monkeypatch) -> Path:
    from hydrahive.archive import location
    root = tmp_path / "archiv"
    monkeypatch.setattr(location, "archive_root", lambda: root)
    return root
