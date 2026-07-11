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
    if bare.startswith(("claude-", "MiniMax-M2")):
        return ("low", "medium", "high")
    return ()
