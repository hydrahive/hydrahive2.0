"""
Tests für den Reasoning-Effort-Pfad.

Zwei Pfade, modellabhängig (apply_effort in llm/_anthropic.py):
  - Claude 4.6+: output_config.effort + thinking.type=adaptive (low..max)
  - Claude 4.5 / älter, MiniMax: Legacy extended_thinking budget_tokens

Flow: Session.metadata.reasoning_effort
  → runner.py liest es per Call aus DB
  → apply_effort(kwargs, model, effort)
  → kwargs["output_config"]["effort"]  (neu)  ODER
    kwargs["thinking"] = {"type": "enabled", "budget_tokens": N}  (legacy)
  → Anthropic API
"""
from hydrahive.llm._anthropic import (
    EFFORT_LEVELS,
    EFFORT_PARAM_MODELS,
    EFFORT_TO_BUDGET,
    apply_effort,
)

# Repräsentative Modelle pro Pfad
_NEW = "claude-opus-4-8"        # adaptive + output_config.effort
_LEGACY = "claude-opus-4-5"     # extended_thinking budget_tokens
_MINIMAX = "MiniMax-M2.7"       # ebenfalls Legacy-Pfad


# ---------------------------------------------------------------------------
# Gemeinsam: kein/leerer/unbekannter Effort ist no-op (beide Pfade)
# ---------------------------------------------------------------------------

def test_kein_effort_ist_noop():
    kwargs = {"model": _NEW, "max_tokens": 4096, "temperature": 0.7}
    apply_effort(kwargs, _NEW, None)
    assert "thinking" not in kwargs
    assert "output_config" not in kwargs
    assert kwargs["temperature"] == 0.7
    assert kwargs["max_tokens"] == 4096


def test_leerer_effort_ist_noop():
    kwargs = {"max_tokens": 4096}
    apply_effort(kwargs, _NEW, "")
    assert "thinking" not in kwargs
    assert "output_config" not in kwargs


def test_unbekannter_effort_neu_ist_noop():
    kwargs = {"max_tokens": 4096}
    apply_effort(kwargs, _NEW, "turbo")
    assert "output_config" not in kwargs
    assert "thinking" not in kwargs


def test_unbekannter_effort_legacy_ist_noop():
    kwargs = {"max_tokens": 4096}
    apply_effort(kwargs, _LEGACY, "turbo")
    assert "thinking" not in kwargs


# ---------------------------------------------------------------------------
# Neuer Pfad: Claude 4.6+ → output_config.effort + adaptive thinking
# ---------------------------------------------------------------------------

def test_neu_low_setzt_output_config_effort():
    kwargs = {"max_tokens": 8192, "temperature": 0.7}
    apply_effort(kwargs, _NEW, "low")
    assert kwargs["output_config"]["effort"] == "low"
    assert kwargs["thinking"] == {"type": "adaptive"}


def test_neu_high_setzt_output_config_effort():
    kwargs = {"max_tokens": 8192}
    apply_effort(kwargs, _NEW, "high")
    assert kwargs["output_config"]["effort"] == "high"


def test_neu_xhigh_erlaubt():
    kwargs = {"max_tokens": 8192}
    apply_effort(kwargs, _NEW, "xhigh")
    assert kwargs["output_config"]["effort"] == "xhigh"


def test_neu_max_erlaubt():
    kwargs = {"max_tokens": 8192}
    apply_effort(kwargs, _NEW, "max")
    assert kwargs["output_config"]["effort"] == "max"


def test_neu_setzt_kein_budget_tokens():
    """Der neue Pfad darf NIE budget_tokens setzen — das wirft auf 4.8 einen 400er."""
    kwargs = {"max_tokens": 8192, "temperature": 0.7}
    apply_effort(kwargs, _NEW, "high")
    assert "budget_tokens" not in kwargs.get("thinking", {})


def test_neu_laesst_temperature_unangetastet():
    """Neuer Pfad: temperature bleibt — der deprecated-Retry im Call kümmert sich."""
    kwargs = {"max_tokens": 8192, "temperature": 0.3}
    apply_effort(kwargs, _NEW, "high")
    assert kwargs["temperature"] == 0.3


def test_neu_laesst_max_tokens_unangetastet():
    kwargs = {"max_tokens": 4096}
    apply_effort(kwargs, _NEW, "xhigh")
    assert kwargs["max_tokens"] == 4096


def test_neu_erkennt_provider_prefix():
    kwargs = {"max_tokens": 8192}
    apply_effort(kwargs, "anthropic/claude-opus-4-8", "high")
    assert kwargs["output_config"]["effort"] == "high"


# ---------------------------------------------------------------------------
# Legacy-Pfad: Claude 4.5/älter + MiniMax → extended_thinking budget_tokens
# ---------------------------------------------------------------------------

def test_legacy_low_setzt_thinking_block():
    kwargs = {"max_tokens": 8192, "temperature": 0.7}
    apply_effort(kwargs, _LEGACY, "low")
    assert kwargs["thinking"] == {"type": "enabled", "budget_tokens": EFFORT_TO_BUDGET["low"]}
    assert "output_config" not in kwargs


def test_legacy_high_setzt_thinking_block():
    kwargs = {"max_tokens": 8192, "temperature": 0.7}
    apply_effort(kwargs, _LEGACY, "high")
    assert kwargs["thinking"]["budget_tokens"] == EFFORT_TO_BUDGET["high"]


def test_legacy_temperature_wird_auf_1_gesetzt():
    kwargs = {"max_tokens": 8192, "temperature": 0.3}
    apply_effort(kwargs, _LEGACY, "medium")
    assert kwargs["temperature"] == 1.0


def test_legacy_max_tokens_hochgezogen_wenn_zu_klein():
    budget = EFFORT_TO_BUDGET["high"]
    kwargs = {"max_tokens": budget, "temperature": 1.0}
    apply_effort(kwargs, _LEGACY, "high")
    assert kwargs["max_tokens"] > budget


def test_legacy_max_tokens_bleibt_wenn_gross_genug():
    kwargs = {"max_tokens": 32768, "temperature": 1.0}
    apply_effort(kwargs, _LEGACY, "high")
    assert kwargs["max_tokens"] == 32768


def test_legacy_xhigh_ist_noop():
    """xhigh existiert im Legacy-Budget-Mapping nicht → kein thinking-Block."""
    kwargs = {"max_tokens": 8192, "temperature": 0.7}
    apply_effort(kwargs, _LEGACY, "xhigh")
    assert "thinking" not in kwargs


def test_minimax_nutzt_legacy_pfad():
    """MiniMax darf NIE output_config bekommen — der Endpoint kennt es nicht."""
    kwargs = {"max_tokens": 8192, "temperature": 0.7}
    apply_effort(kwargs, _MINIMAX, "medium")
    assert kwargs["thinking"]["type"] == "enabled"
    assert "output_config" not in kwargs


# ---------------------------------------------------------------------------
# Konstanten / Tabellen
# ---------------------------------------------------------------------------

def test_budget_steigt_mit_effort_level():
    assert EFFORT_TO_BUDGET["low"] < EFFORT_TO_BUDGET["medium"] < EFFORT_TO_BUDGET["high"]


def test_effort_levels_vollstaendig():
    assert EFFORT_LEVELS == ("low", "medium", "high", "xhigh", "max")


def test_opus_4_8_in_effort_param_models():
    assert any("claude-opus-4-8".startswith(p) for p in EFFORT_PARAM_MODELS)


def test_sonnet_4_6_in_effort_param_models():
    assert any("claude-sonnet-4-6".startswith(p) for p in EFFORT_PARAM_MODELS)


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
    assert _is_claude_model("claude-opus-4-8")
    assert _is_claude_model("anthropic/claude-haiku-4-5")


def test_non_claude_modelle_nicht_erkannt():
    assert not _is_claude_model("gpt-4o")
    assert not _is_claude_model("nvidia_nim/meta/llama-3.1-70b")
    assert not _is_claude_model("minimax/minimax-text-01")
    assert not _is_claude_model("")
