"""LLM-Pricing-Lookup für Cost-Tracking (Mikro-Cents).

Preise in **Mikro-Cents pro Token** (1 Cent = 1000 Micros). Quelle: offizielle
Anbieter-Pricing-Pages, Stand 2026-05-11. Veraltete Werte bei Modell-Refresh
hier aktualisieren — diese Datei ist die einzige Quelle.

Mapping `(provider, model)` → 4 Raten. Für nicht-gelistete Modelle: None →
Cost wird nicht berechnet (NULL in DB), Token-Counts bleiben unverändert.
"""
from __future__ import annotations

from typing import NamedTuple


class Pricing(NamedTuple):
    """Mikro-Cents pro Token, je Phase."""
    input: float
    output: float
    cache_read: float
    cache_creation: float


# Anthropic Claude — $/1M tokens × 100 cents × 1000 micros / 1M tokens = $-Wert × 0.1 micros/token
# Beispiel: Sonnet $3/1M input = 3 × 0.1 = 0.3 micros/token
_ANTHROPIC: dict[str, Pricing] = {
    # Sonnet 5: $2 / $10 / cache_read $0.20 / cache_write $2.50 (Intro-Preis, Stand 2026-07)
    "claude-sonnet-5": Pricing(0.2, 1.0, 0.02, 0.25),
    # Sonnet 4.x (4-5, 4-6, 4-7): $3 / $15 / cache_read $0.30 / cache_write $3.75
    "claude-sonnet-4": Pricing(0.3, 1.5, 0.03, 0.375),
    # Opus 4.x (4-5, 4-6, 4-7): $15 / $75 / $1.50 / $18.75
    "claude-opus-4": Pricing(1.5, 7.5, 0.15, 1.875),
    # Haiku 4.x: $1 / $5 / $0.10 / $1.25
    "claude-haiku-4": Pricing(0.1, 0.5, 0.01, 0.125),
    # Claude 3.7 Sonnet: $3 / $15
    "claude-3-7-sonnet": Pricing(0.3, 1.5, 0.03, 0.375),
    # Claude 3.5 Sonnet: $3 / $15
    "claude-3-5-sonnet": Pricing(0.3, 1.5, 0.03, 0.375),
    # Claude 3.5 Haiku: $0.80 / $4
    "claude-3-5-haiku": Pricing(0.08, 0.4, 0.008, 0.1),
}

# OpenAI — Stand 2026-05
_OPENAI: dict[str, Pricing] = {
    # GPT-5: hypothetisch — falls verfügbar, anpassen
    "gpt-5": Pricing(2.5, 10.0, 0.25, 2.5),
    # GPT-4o: $2.50 / $10
    "gpt-4o": Pricing(0.25, 1.0, 0.025, 0.25),
    "gpt-4o-mini": Pricing(0.015, 0.06, 0.0015, 0.015),
    "gpt-4-turbo": Pricing(1.0, 3.0, 0.0, 0.0),
}

# Provider-Mapping. Cache-Felder = 0.0 wenn der Provider kein Caching liefert.
_DEEPSEEK: dict[str, Pricing] = {
    "deepseek-chat": Pricing(0.027, 0.11, 0.007, 0.027),
    "deepseek-reasoner": Pricing(0.055, 0.22, 0.014, 0.055),
}

_GEMINI: dict[str, Pricing] = {
    "gemini-2.0-flash": Pricing(0.01, 0.04, 0.0025, 0.01),
    "gemini-2.0-pro": Pricing(0.125, 0.5, 0.03125, 0.125),
    "gemini-1.5-pro": Pricing(0.125, 0.5, 0.03125, 0.125),
    "gemini-1.5-flash": Pricing(0.0075, 0.03, 0.001875, 0.0075),
}


def provider_from_model(model: str) -> str:
    """Heuristik: Provider aus Modell-Name ableiten. Erweiterbar wenn neue
    Provider dazukommen. Default 'other' wenn nicht erkannt."""
    m = model.lower()
    if m.startswith("claude") or "anthropic" in m:
        return "anthropic"
    if m.startswith("gpt") or m.startswith("o1") or m.startswith("o3"):
        return "openai"
    if m.startswith("deepseek"):
        return "deepseek"
    if m.startswith("gemini") or m.startswith("google"):
        return "gemini"
    if m.startswith("qwen"):
        return "qwen"
    if m.startswith("llama") or m.startswith("mistral") or m.startswith("mixtral"):
        return "ollama"
    if "minimax" in m:
        return "minimax"
    if m.startswith("openrouter/"):
        return "openrouter"
    return "other"


def _match(model: str, table: dict[str, Pricing]) -> Pricing | None:
    """Prefix-Match: 'claude-sonnet-4-7-20251015' matcht 'claude-sonnet-4'."""
    m = model.lower()
    # Sortiert nach Länge absteigend → spezifischer Match gewinnt vor generischem
    for prefix in sorted(table.keys(), key=len, reverse=True):
        if m.startswith(prefix):
            return table[prefix]
    return None


def lookup(provider: str, model: str) -> Pricing | None:
    """Findet Pricing für (provider, model). None wenn unbekannt."""
    p = provider.lower()
    if p == "anthropic":
        return _match(model, _ANTHROPIC)
    if p == "openai":
        return _match(model, _OPENAI)
    if p == "deepseek":
        return _match(model, _DEEPSEEK)
    if p in {"gemini", "google"}:
        return _match(model, _GEMINI)
    if p == "openrouter":
        return None  # Option A: kein per-Modell-Pricing; Tokens werden gezählt, Kosten als NULL
    return None


def cost_micros(
    provider: str,
    model: str,
    *,
    prompt_tokens: int,
    completion_tokens: int,
    cache_read_tokens: int,
    cache_creation_tokens: int,
) -> int | None:
    """Berechnet Kosten in Mikro-Cents. None wenn Pricing unbekannt."""
    p = lookup(provider, model)
    if p is None:
        return None
    # Wichtig: prompt_tokens enthält bei Anthropic NICHT die cache-tokens
    # (die werden separat ausgewiesen). Wir summieren alle vier Buckets.
    total = (
        prompt_tokens * p.input
        + completion_tokens * p.output
        + cache_read_tokens * p.cache_read
        + cache_creation_tokens * p.cache_creation
    )
    return int(round(total))
