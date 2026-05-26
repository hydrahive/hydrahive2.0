"""Smoke-Tests für Zahnfee — JSON-Parsing und Briefing-Storage."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# _extract_json — pure Funktion, kein I/O
# ---------------------------------------------------------------------------

from hydrahive.zahnfee.runner import _extract_json


def test_extract_json_plain():
    raw = '{"open": "Ticket XY", "went_well": "Deploy", "went_badly": "", "today": "Review"}'
    result = _extract_json(raw)
    assert result["open"] == "Ticket XY"
    assert result["today"] == "Review"


def test_extract_json_markdown_fenced():
    raw = '```json\n{"open": "a", "went_well": "b", "went_badly": "c", "today": "d"}\n```'
    result = _extract_json(raw)
    assert result["open"] == "a"
    assert result["went_well"] == "b"


def test_extract_json_markdown_sections():
    raw = "## Offen\nTicket 123\n## Gut gelaufen\nDeploy OK\n## Schlecht gelaufen\nNichts\n## Heute\nReview"
    result = _extract_json(raw)
    assert "Ticket 123" in result["open"]
    assert "Deploy OK" in result["went_well"]


def test_extract_json_fallback_garbage():
    raw = "Keine JSON-Struktur vorhanden, nur Fließtext."
    result = _extract_json(raw)
    assert "open" in result
    assert result["open"]


# ---------------------------------------------------------------------------
# storage.save / storage.load — round-trip
# ---------------------------------------------------------------------------

def test_briefing_save_and_load(setup_test_env, monkeypatch):
    from hydrahive.zahnfee import storage
    from hydrahive.settings import settings

    briefing = storage.Briefing(
        generated_at="2026-05-26T08:00:00+00:00",
        date="2026-05-26",
        open_items="Ticket XY",
        went_well="Deploy",
        went_badly="",
        today="Review",
    )
    storage.save(briefing)
    loaded = storage.load()

    assert loaded is not None
    assert loaded.date == "2026-05-26"
    assert loaded.open_items == "Ticket XY"
    assert loaded.went_well == "Deploy"
    assert loaded.error is None


def test_briefing_load_returns_none_when_missing(setup_test_env):
    from hydrahive.zahnfee import storage

    path = storage._path()
    if path.exists():
        path.unlink()

    assert storage.load() is None
