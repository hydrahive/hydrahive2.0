"""Gemeinsamer, sequenzieller LLM-Aufruf für Compaction-Summaries."""
from __future__ import annotations

import logging
import re

from hydrahive.compaction.tokens import context_window_for, estimate_dense_text

logger = logging.getLogger(__name__)

# Nur für Compaction: Ein nicht erreichbarer Provider (z. B. Ollama aus) soll auf das nächste konfigurierte Modell
# wechseln. Bewusst NICHT in runner/_failover.py – der Chat-Pfad behandelt Verbindungsfehler mit seinem eigenen
# Stream-Retry und soll dafür nicht das Modell wechseln (#205, Review 09.11.2026).
_CONNECTION_PATTERNS = (
    re.compile(r"\bapi.?connection(?:error)?\b"),
    re.compile(r"\bcannot connect\b"),
    re.compile(r"\bconnect(?:ion)? (?:call failed|refused|reset)\b"),
    re.compile(r"\btimed? ?out\b"),
)


class SummaryTooLarge(RuntimeError):
    """Der Prompt wäre größer als das Modell-Fenster und wird nicht gesendet."""


def guard(model: str, *texts: str) -> None:
    need = sum(estimate_dense_text(text) for text in texts if text)
    window = context_window_for(model)
    if need > window:
        raise SummaryTooLarge(
            f"Zusammenfassung zu groß für {model}: etwa {need} > {window} Tokens – nicht gesendet"
        )


def should_switch_model(exc: Exception) -> bool:
    from hydrahive.runner._failover import should_failover

    if should_failover(exc):
        return True
    text = str(exc).lower()
    return any(pattern.search(text) for pattern in _CONNECTION_PATTERNS)


def _compaction_model(model: str) -> str:
    """MiniMax kann bei Summary-Prompts Web-Search aktivieren und HTTP 500 liefern."""
    from hydrahive.llm._anthropic import is_minimax_model

    if not is_minimax_model(model):
        return model
    from hydrahive.llm._config import load_config

    cfg = load_config()
    default = cfg.get("default_model", "")
    if default and not is_minimax_model(default):
        logger.info("Compaction: MiniMax → Fallback auf %s", default)
        return default
    for provider in cfg.get("providers", []):
        if provider.get("id") == "anthropic" and (provider.get("api_key") or provider.get("oauth")):
            fallback = "claude-haiku-4-5-20251001"
            logger.info("Compaction: MiniMax → Fallback auf %s (Anthropic-Provider)", fallback)
            return fallback
    logger.warning("Compaction: MiniMax-Modell %s, kein non-MiniMax-Fallback — wird scheitern", model)
    return model


def model_chain(primary: str, fallbacks: list[str] | None = None) -> list[str]:
    """Nur konfigurierte Modelle, in Reihenfolge und ohne Duplikate."""
    result: list[str] = []
    for candidate in [primary, *(fallbacks or [])]:
        resolved = _compaction_model(candidate)
        if resolved and resolved not in result:
            result.append(resolved)
    return result


async def call_summary(model: str, *, system_prompt: str, content: str, max_tokens: int) -> str:
    """Ein Summary-Aufruf an genau ein Modell. Der Modellwechsel passiert eine Ebene höher (summarize.py),
    damit bei einem Wechsel passend zum Fenster des neuen Modells neu zerlegt werden kann."""
    guard(model, system_prompt, content)
    from hydrahive.runner.llm_bridge import call_with_tools

    blocks, _, _ = await call_with_tools(
        model=model,
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": content}],
        tools=[],
        temperature=0.3,
        max_tokens=max_tokens,
    )
    parts = [block.get("text", "") for block in blocks if block.get("type") == "text"]
    return "\n".join(part for part in parts if part).strip()
