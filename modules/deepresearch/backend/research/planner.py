"""Schritt 1: Plan — Teil-Fragen + Kategorie aus der Nutzerfrage."""
from __future__ import annotations

from . import prompts
from .llm import ask, parse_json
from .models import RunState

_CATEGORIES = {"product", "comparison", "howto", "factcheck", "general"}


async def make_plan(state: RunState) -> None:
    """Befüllt state.subquestions und state.category (mutiert state in-place)."""
    system = prompts.SYSTEM.format(date=prompts.today_str())
    raw = await ask(prompts.plan(state.question), model=state.model, system=system, max_tokens=600)
    data = parse_json(raw, {})

    subs = data.get("subquestions") if isinstance(data, dict) else None
    state.subquestions = [str(s).strip() for s in subs if str(s).strip()][:5] if isinstance(subs, list) else []
    if not state.subquestions:
        state.subquestions = [state.question]  # Fallback: nackte Frage

    cat = str(data.get("category", "general")).strip().lower() if isinstance(data, dict) else "general"
    state.category = cat if cat in _CATEGORIES else "general"
