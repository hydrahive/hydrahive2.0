"""Schritt 3 (pro Quelle): zielgerichtete Extraktion einer Seite zu einem Finding."""
from __future__ import annotations

from . import prompts
from .llm import ask, parse_json
from .models import Finding, RunState


async def extract_finding(state: RunState, result: dict, text: str, image: str) -> Finding | None:
    """LLM-Extraktion. Liefert None, wenn die Seite irrelevant/leer ist."""
    if not text.strip():
        return None
    system = prompts.SYSTEM.format(date=prompts.today_str())
    raw = await ask(
        prompts.extract(state.question, result.get("title", ""), result["url"], text),
        model=state.model,
        system=system,
        max_tokens=700,
    )
    data = parse_json(raw, {})
    if not isinstance(data, dict) or not data.get("relevant", False):
        return None
    summary = str(data.get("summary", "")).strip()
    if not summary:
        return None
    return Finding(
        url=result["url"],
        title=result.get("title", "") or result["url"],
        summary=summary,
        evidence=str(data.get("evidence", "")).strip(),
        image=image,
    )
