"""
Tests für den Reasoning-Effort-Pfad (Extended Thinking).

Flow: Session.metadata.reasoning_effort
  → runner.py liest es per Call aus DB
  → apply_thinking_budget(kwargs, effort) in llm/_anthropic.py
  → kwargs["thinking"] = {"type": "enabled", "budget_tokens": N}
  → Anthropic API
"""
import pytest
from hydrahive.llm._anthropic import EFFORT_TO_BUDGET, apply_thinking_budget


# ---------------------------------------------------------------------------
# apply_thinking_budget — die zentrale Funktion
# ---------------------------------------------------------------------------

def test_kein_effort_ist_noop():
    kwargs = {"model": "claude-sonnet-4-6", "max_tokens": 4096, "temperature": 0.7}
    apply_thinking_budget(kwargs, None)
    assert "thinking" not in kwargs
    assert kwargs["temperature"] == 0.7
    assert kwargs["max_tokens"] == 4096


def test_leerer_effort_ist_noop():
    kwargs = {"max_tokens": 4096}
    apply_thinking_budget(kwargs, "")
    assert "thinking" not in kwargs


def test_unbekannter_effort_ist_noop():
    kwargs = {"max_tokens": 4096}
    apply_thinking_budget(kwargs, "ultra")
    assert "thinking" not in kwargs


def test_low_effort_setzt_thinking_block():
    kwargs = {"max_tokens": 8192, "temperature": 0.7}
    apply_thinking_budget(kwargs, "low")
    assert kwargs["thinking"] == {"type": "enabled", "budget_tokens": EFFORT_TO_BUDGET["low"]}


def test_medium_effort_setzt_thinking_block():
    kwargs = {"max_tokens": 8192, "temperature": 0.7}
    apply_thinking_budget(kwargs, "medium")
    assert kwargs["thinking"]["type"] == "enabled"
    assert kwargs["thinking"]["budget_tokens"] == EFFORT_TO_BUDGET["medium"]


def test_high_effort_setzt_thinking_block():
    kwargs = {"max_tokens": 8192, "temperature": 0.7}
    apply_thinking_budget(kwargs, "high")
    assert kwargs["thinking"]["budget_tokens"] == EFFORT_TO_BUDGET["high"]


def test_temperature_wird_auf_1_gesetzt():
    """Anthropic erlaubt mit Extended Thinking nur temperature=1.0."""
    kwargs = {"max_tokens": 8192, "temperature": 0.3}
    apply_thinking_budget(kwargs, "medium")
    assert kwargs["temperature"] == 1.0


def test_max_tokens_wird_hochgezogen_wenn_zu_klein():
    """Anthropic verlangt max_tokens > budget_tokens."""
    budget = EFFORT_TO_BUDGET["high"]
    kwargs = {"max_tokens": budget, "temperature": 1.0}  # gleich = zu wenig
    apply_thinking_budget(kwargs, "high")
    assert kwargs["max_tokens"] > budget


def test_max_tokens_bleibt_wenn_gross_genug():
    kwargs = {"max_tokens": 32768, "temperature": 1.0}
    apply_thinking_budget(kwargs, "high")
    assert kwargs["max_tokens"] == 32768


def test_budget_steigt_mit_effort_level():
    """low < medium < high — sonst wäre die Abstufung sinnlos."""
    assert EFFORT_TO_BUDGET["low"] < EFFORT_TO_BUDGET["medium"] < EFFORT_TO_BUDGET["high"]


def test_alle_effort_levels_definiert():
    for level in ("low", "medium", "high"):
        assert level in EFFORT_TO_BUDGET
        assert EFFORT_TO_BUDGET[level] > 0


# ---------------------------------------------------------------------------
# isClaudeModel-Logik (Frontend-Äquivalent im Backend nachgebaut)
# ---------------------------------------------------------------------------

def _is_claude_model(model: str) -> bool:
    """Spiegelt die Frontend-Logik aus _ChatHeader.tsx:
    activeModel.replace(/^anthropic[/]/, "").startsWith("claude-")
    """
    return model.replace("anthropic/", "", 1).startswith("claude-")


def test_claude_modelle_erkannt():
    assert _is_claude_model("claude-sonnet-4-6")
    assert _is_claude_model("claude-opus-4-7")
    assert _is_claude_model("anthropic/claude-haiku-4-5")


def test_non_claude_modelle_nicht_erkannt():
    assert not _is_claude_model("gpt-4o")
    assert not _is_claude_model("nvidia_nim/meta/llama-3.1-70b")
    assert not _is_claude_model("minimax/minimax-text-01")
    assert not _is_claude_model("")
