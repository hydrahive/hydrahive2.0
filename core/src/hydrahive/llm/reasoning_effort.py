"""Modellabhängige Reasoning-Effort-Fähigkeiten des Codex-Clients."""
from __future__ import annotations

_STANDARD = ("low", "medium", "high", "xhigh")
_WITH_MAX = (*_STANDARD, "max")
_WITH_ULTRA = (*_WITH_MAX, "ultra")


def effort_levels_for_model(model: str) -> tuple[str, ...]:
    """Erlaubte Effort-Werte für ein Modell, leer wenn nicht unterstützt."""
    bare = model.removeprefix("anthropic/")
    if model.startswith(("openai-codex/gpt-5.6-sol", "openai-codex/gpt-5.6-terra")):
        return _WITH_ULTRA
    if model.startswith("openai-codex/gpt-5.6-luna"):
        return _WITH_MAX
    if model.startswith("openai-codex/"):
        return _STANDARD
    if bare.startswith("claude-"):
        # Claude 4.6+ nutzt output_config.effort (low..max inkl. xhigh/max);
        # ältere Claude-Modelle nutzen den Legacy-Budget-Pfad (low/medium/high).
        # _anthropic.py ist die einzige Wahrheitsquelle — hier nur ableiten.
        from hydrahive.llm._anthropic import EFFORT_LEVELS, _uses_effort_param
        if _uses_effort_param(model):
            return EFFORT_LEVELS
        return ("low", "medium", "high")
    if bare.startswith("MiniMax-M2"):
        return ("low", "medium", "high")
    return ()
