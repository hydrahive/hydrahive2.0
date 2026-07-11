"""Modellabhängige Reasoning-Effort-Fähigkeiten."""
from __future__ import annotations

_CODEX_BASE = ("minimal", "low", "medium", "high")
_CODEX_XHIGH = ("none", "low", "medium", "high", "xhigh")
_CODEX_MAX = (*_CODEX_XHIGH, "max")


def effort_levels_for_model(model: str) -> tuple[str, ...]:
    """Erlaubte Effort-Werte für ein Modell, leer wenn nicht unterstützt."""
    bare = model.removeprefix("anthropic/")
    if model.startswith("openai-codex/gpt-5.6-"):
        return _CODEX_MAX
    if model.startswith(("openai-codex/gpt-5.5", "openai-codex/gpt-5.4")):
        return _CODEX_XHIGH
    if model.startswith("openai-codex/"):
        return _CODEX_BASE
    if bare.startswith(("claude-", "MiniMax-M2")):
        return ("low", "medium", "high")
    return ()
