"""Tests für DEFAULT_MAX_ITERATIONS 30→16 + Per-Agent-Override (#125 redo)."""
from __future__ import annotations

import pytest

from hydrahive.agents._config_utils import normalize
from hydrahive.agents._defaults import DEFAULT_MAX_ITERATIONS
from hydrahive.agents._validation import (
    AgentValidationError,
    normalize_compact_changes,
    validate_max_iterations,
)


def test_default_ist_16():
    assert DEFAULT_MAX_ITERATIONS == 16


def test_normalize_setzt_default_bei_fehlendem_feld():
    cfg = {"id": "a1", "name": "test"}
    out = normalize(cfg)
    assert out["max_iterations"] == 16


def test_normalize_respektiert_expliziten_user_wert():
    cfg = {"id": "a1", "name": "test", "max_iterations": 30}
    out = normalize(cfg)
    assert out["max_iterations"] == 30


def test_validation_min_ist_1():
    validate_max_iterations(1)
    validate_max_iterations(16)
    validate_max_iterations(50)
    validate_max_iterations(100)
    with pytest.raises(AgentValidationError, match="≥ 1"):
        validate_max_iterations(0)


def test_validation_max_ist_100():
    with pytest.raises(AgentValidationError, match="exzessiv"):
        validate_max_iterations(101)
    with pytest.raises(AgentValidationError, match="exzessiv"):
        validate_max_iterations(1000)


def test_validation_kein_int_fehl():
    with pytest.raises(AgentValidationError):
        validate_max_iterations("16")  # type: ignore[arg-type]
    with pytest.raises(AgentValidationError):
        validate_max_iterations(None)  # type: ignore[arg-type]


def test_normalize_compact_changes_validiert_max_iterations():
    """Update-Pfad: max_iterations im changes-Dict wird validiert."""
    changes = {"max_iterations": 32}
    normalize_compact_changes(changes)
    assert changes["max_iterations"] == 32

    changes_bad = {"max_iterations": 200}
    with pytest.raises(AgentValidationError, match="exzessiv"):
        normalize_compact_changes(changes_bad)


def test_normalize_compact_changes_entfernt_none():
    changes = {"max_iterations": None}
    normalize_compact_changes(changes)
    assert "max_iterations" not in changes


def test_runner_max_iterations_module_default():
    """Modul-Konstante zeigt auf den neuen Default."""
    from hydrahive.runner.runner import MAX_ITERATIONS
    assert MAX_ITERATIONS == 16
