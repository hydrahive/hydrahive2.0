"""Tests für DEFAULT_MAX_TOKENS 8192 → 16384 (#142).

Begründung: bei Opus+Thinking frisst das Thinking-Budget einen Teil des
max_tokens-Pots. Plus tool_use-Inputs mit großen content-Strings (16kB
Markdown via file_write → ~4-5k Tokens Input-JSON). 8192 reichte nicht;
test_10 verlor 20% der Session-Kosten an stop_reason=max_tokens-Restarts.
"""
from __future__ import annotations

import pytest

from hydrahive.agents._config_utils import normalize
from hydrahive.agents._defaults import DEFAULT_MAX_TOKENS
from hydrahive.agents._validation import AgentValidationError, validate_max_tokens


def test_default_ist_16384():
    assert DEFAULT_MAX_TOKENS == 16384


def test_normalize_backfillt_default_bei_fehlendem_feld():
    cfg = {"id": "a1", "name": "test"}
    out = normalize(cfg)
    assert out["max_tokens"] == 16384


def test_normalize_respektiert_expliziten_user_wert():
    """Bestehende Configs mit eigenem max_tokens bleiben unverändert."""
    cfg = {"id": "a1", "name": "test", "max_tokens": 4096}
    out = normalize(cfg)
    assert out["max_tokens"] == 4096


def test_validation_akzeptiert_default():
    validate_max_tokens(DEFAULT_MAX_TOKENS)


def test_validation_akzeptiert_high_und_low():
    validate_max_tokens(1)
    validate_max_tokens(200_000)


def test_validation_lehnt_negative_ab():
    with pytest.raises(AgentValidationError):
        validate_max_tokens(0)
    with pytest.raises(AgentValidationError):
        validate_max_tokens(-1)


def test_validation_lehnt_zu_gross_ab():
    with pytest.raises(AgentValidationError):
        validate_max_tokens(200_001)


def test_agent_schema_default_ist_default_max_tokens():
    """AgentCreate-Schema soll DEFAULT_MAX_TOKENS als Default haben, nicht 4096."""
    from hydrahive.api.routes._agent_schemas import AgentCreate
    fields = AgentCreate.model_fields
    assert fields["max_tokens"].default == DEFAULT_MAX_TOKENS


def test_runner_kein_hardcoded_4096_fallback():
    """Schutz vor Regression — die hardcoded 4096-Fallbacks in runner.py
    waren historisch und sollten DEFAULT_MAX_TOKENS nutzen."""
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "src" / "hydrahive" / "runner" / "runner.py"
    content = src.read_text(encoding="utf-8")
    assert "4096" not in content, (
        "runner.py enthält hardcoded 4096 — sollte DEFAULT_MAX_TOKENS sein"
    )
