"""Dünner LLM-Wrapper für den Research-Loop.

Geht über hydrahive.llm.client.complete() — damit lokale Modelle (Ollama/LM-Studio/
OpenAI-kompatibel via LiteLLM) genauso funktionieren wie Cloud-Modelle. Zusätzlich:
- <think>…</think> von Reasoning-Modellen wird entfernt
- robustes JSON-Parsing für schwache lokale Modelle (Codeblock-Fences, Vorgeplapper)
"""
from __future__ import annotations

import json
import re

from hydrahive.llm.client import complete

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def strip_thinking(text: str) -> str:
    return _THINK.sub("", text or "").strip()


async def ask(
    prompt: str,
    *,
    model: str | None = None,
    system: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    out = await complete(messages, model=model, temperature=temperature, max_tokens=max_tokens)
    return strip_thinking(out or "")


def _first_json_blob(text: str, opener: str, closer: str) -> str | None:
    """Erstes balanciertes {…} bzw. […] aus rohem LLM-Text schneiden."""
    start = text.find(opener)
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def parse_json(text: str, default):
    """JSON aus LLM-Antwort lesen; bei Misserfolg default zurückgeben (kein Crash)."""
    text = strip_thinking(text)
    fence = _FENCE.search(text)
    if fence:
        text = fence.group(1)
    for opener, closer in (("[", "]"), ("{", "}")):
        blob = _first_json_blob(text, opener, closer)
        if blob:
            try:
                return json.loads(blob)
            except (ValueError, TypeError):
                continue
    try:
        return json.loads(text.strip())
    except (ValueError, TypeError):
        return default
