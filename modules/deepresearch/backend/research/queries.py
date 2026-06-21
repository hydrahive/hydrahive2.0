"""Schritt 2 (pro Runde): Suchanfragen erzeugen, dedupliziert gegen bereits genutzte."""
from __future__ import annotations

from . import prompts
from .llm import ask, parse_json
from .models import RunState


async def generate_queries(state: RunState, first_round: bool) -> list[str]:
    system = prompts.SYSTEM.format(date=prompts.today_str())
    raw = await ask(
        prompts.queries(state.question, state.subquestions, first_round, sorted(state.queries_used)),
        model=state.model,
        system=system,
        max_tokens=400,
    )
    arr = parse_json(raw, [])
    if not isinstance(arr, list):
        arr = []

    fresh: list[str] = []
    for q in arr:
        q = str(q).strip()
        key = q.lower()
        if q and key not in state.queries_used:
            state.queries_used.add(key)
            fresh.append(q)
    if not fresh and first_round:
        # Hartes Fallback, damit Runde 1 nie leer ausgeht
        fresh = [state.question]
        state.queries_used.add(state.question.lower())
    return fresh
