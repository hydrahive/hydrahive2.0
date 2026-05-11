"""Tests für Memory-Injection-Defaults (Token-Audit-Optimierung)."""
from __future__ import annotations

from hydrahive.agents._defaults import (
    DEFAULT_MEMORY_MAX_CHARS,
    DEFAULT_MEMORY_MAX_CRYSTALS,
    DEFAULT_MEMORY_MAX_LESSONS,
)


def test_crystal_default_ist_3():
    assert DEFAULT_MEMORY_MAX_CRYSTALS == 3


def test_lessons_default_ist_6():
    assert DEFAULT_MEMORY_MAX_LESSONS == 6


def test_max_chars_default_ist_2500():
    assert DEFAULT_MEMORY_MAX_CHARS == 2500


def test_normalize_setzt_neue_defaults_bei_fehlendem_feld():
    from hydrahive.agents._config_utils import normalize
    cfg = {"id": "a1", "name": "test"}
    out = normalize(cfg)
    assert out["memory_max_crystals"] == 3
    assert out["memory_max_lessons"] == 6
    assert out["memory_max_chars"] == 2500


def test_normalize_respektiert_expliziten_user_wert():
    from hydrahive.agents._config_utils import normalize
    cfg = {"id": "a1", "name": "test",
           "memory_max_crystals": 8, "memory_max_lessons": 15}
    out = normalize(cfg)
    assert out["memory_max_crystals"] == 8
    assert out["memory_max_lessons"] == 15
