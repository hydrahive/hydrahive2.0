"""Direkter anthropic-SDK-Pfad für Claude-Modelle und MiniMax (anthropic-kompatibel).

Vorteile gegenüber LiteLLM für diese beiden:
- volle Anthropic-Features (Prompt-Caching, Extended Thinking, Image-Blocks,
  Citations, Tool-Streaming) ohne Übersetzungsverlust
- ein konsistenter Pfad für OAuth- + Plain-Bearer-Tokens
"""
from __future__ import annotations

_OAUTH_HEADERS = {
    "anthropic-beta": "claude-code-20250219,oauth-2025-04-20,fine-grained-tool-streaming-2025-05-14,prompt-caching-2024-07-31",
    "user-agent": "claude-cli/2.1.62",
    "x-app": "cli",
}

_OAUTH_IDENTITY = [
    {"type": "text", "text": "You are Claude Code, Anthropic's official CLI for Claude."}
]

# api.minimax.io = Global Platform; api.minimaxi.com = China — nicht kreuzkompatibel.
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"

# Gültige effort-Stufen für den neuen output_config.effort-Pfad (Claude 4.6+).
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

# Claude-Modelle mit adaptive thinking + output_config.effort (4.6 und neuer).
# Alle anderen (Claude 4.5/4.1/4.0/3.x, MiniMax) nutzen den Legacy-Pfad.
EFFORT_PARAM_MODELS = (
    "claude-opus-5", "claude-opus-4-6", "claude-opus-4-7", "claude-opus-4-8", "claude-sonnet-4-6",
    "claude-sonnet-5", "claude-fable-5",
)

# Legacy: Reasoning-Effort → extended_thinking budget_tokens (Claude 4.5/älter, MiniMax).
# Auswahl bewusst niedrig: high = 16k Tokens reicht für die meisten Tool-Loops.
EFFORT_TO_BUDGET = {"low": 1024, "medium": 4096, "high": 16384}


def _uses_effort_param(model: str) -> bool:
    """True für Claude 4.6+ (adaptive thinking + output_config.effort)."""
    bare = strip_provider_prefix(model)
    return any(bare.startswith(p) for p in EFFORT_PARAM_MODELS)


def apply_effort(kwargs: dict, model: str, effort: str | None) -> None:
    """Setzt Reasoning-Effort modellabhängig (mutiert kwargs in-place).

    Neuer Pfad (Claude 4.6+): output_config.effort (low..max) + thinking.adaptive.
    Adaptive thinking verlangt temperature=1 (sonst 400 „may only be set to 1
    when thinking is enabled or in adaptive mode“, Task 48278afd). Ist temperature
    gesetzt, wird sie auf 1.0 gezogen; fehlt sie, bleibt sie weg. Modelle, die
    temperature ganz ablehnen, fängt weiter der deprecated-Retry im Call-Layer ab.
    max_tokens bleibt unangetastet.

    Legacy-Pfad (Claude 4.5/älter, MiniMax): extended_thinking budget_tokens
    (nur low/medium/high), temperature=1.0, max_tokens hochgezogen.

    Bei effort=None/leer oder unbekanntem Wert: kein-op.
    """
    if not effort:
        return
    if _uses_effort_param(model):
        if effort not in EFFORT_LEVELS:
            return
        kwargs["thinking"] = {"type": "adaptive"}
        kwargs.setdefault("output_config", {})["effort"] = effort
        if "temperature" in kwargs:
            kwargs["temperature"] = 1.0
        return
    budget = EFFORT_TO_BUDGET.get(effort)
    if budget is None:
        return
    kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
    if kwargs.get("max_tokens", 0) <= budget:
        kwargs["max_tokens"] = budget + 4096
    kwargs["temperature"] = 1.0


def strip_provider_prefix(model: str) -> str:
    """Removes 'anthropic/' or 'minimax/' prefix for direct SDK calls."""
    for prefix in ("anthropic/", "minimax/"):
        if model.startswith(prefix):
            return model[len(prefix):]
    return model


def extract_text(content) -> str:
    """Joined alle Text-Blocks aus einer Anthropic-SDK-Response.
    Skipped ThinkingBlocks (haben kein .text bei Extended Thinking / MiniMax)."""
    parts = [getattr(b, "text", "") for b in content if getattr(b, "type", None) == "text"]
    return "".join(parts)


def is_minimax_model(model: str) -> bool:
    if model.startswith("minimax/"):
        return True
    return strip_provider_prefix(model).lower().startswith("minimax-")


def convert_images_for_minimax(messages: list[dict]) -> list[dict]:
    """Anthropic image blocks → OpenAI image_url blocks für MiniMax.

    MiniMax's /anthropic Endpoint übergibt Anthropic-Image-Blöcke nicht ans Modell.
    Das Modell erwartet intern OpenAI-Format: {type:"image_url",image_url:{url:"data:..."}}.
    """
    result = []
    for m in messages:
        if m.get("role") == "user" and isinstance(m.get("content"), list):
            new_content = []
            for b in m["content"]:
                if isinstance(b, dict) and b.get("type") == "image":
                    source = b.get("source") or {}
                    data = source.get("data", "")
                    mime = source.get("media_type") or "image/png"
                    new_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{data}"},
                    })
                else:
                    new_content.append(b)
            result.append({**m, "content": new_content})
        else:
            result.append(m)
    return result


# complete/stream-Aufrufe (Claude direkt + MiniMax) liegen in _anthropic_calls.py.
