"""Crystal-Kontext-Injection: vergangene Sessions in den System-Prompt einweben.

Lädt beim Session-Start:
  - Letzte 5 Crystals (Narrative + Key Outcomes)
  - Lessons (lesson.*-Keys mit confidence >= 0.6), sortiert nach Confidence

Gibt einen kompakten Markdown-Block zurück, oder None wenn nichts vorhanden.
Kein LLM-Call — rein deterministisch aus gespeicherten Daten.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_MAX_CRYSTALS = 5
_MAX_LESSONS = 10
_MIN_LESSON_CONFIDENCE = 0.6
_MAX_CHARS = 4000  # Soft-Limit für den gesamten Injektionsblock


def build_memory_context(
    agent_id: str,
    project_id: str | None = None,
) -> str | None:
    """
    Baut den Memory-Kontext-Block für den System-Prompt.
    Gibt None zurück wenn weder Crystals noch Lessons vorhanden.
    """
    crystals_text = _format_crystals(agent_id, project_id)
    lessons_text = _format_lessons(agent_id, project_id)

    if not crystals_text and not lessons_text:
        return None

    parts: list[str] = ["## Memory — What I've learned in past sessions\n"]
    if crystals_text:
        parts.append(crystals_text)
    if lessons_text:
        parts.append(lessons_text)

    block = "\n".join(parts)

    # Soft-Limit: kürzen wenn zu lang
    if len(block) > _MAX_CHARS:
        block = block[:_MAX_CHARS] + f"\n[... {len(block) - _MAX_CHARS} chars truncated]"

    return block


def _format_crystals(agent_id: str, project_id: str | None) -> str:
    try:
        from hydrahive.tools._crystallize import list_crystals
        crystals = list_crystals(agent_id, project=project_id, limit=_MAX_CRYSTALS)
    except Exception as e:
        logger.debug("Crystal-Injection: list_crystals fehlgeschlagen: %s", e)
        return ""

    if not crystals:
        return ""

    lines: list[str] = ["### Recent Sessions\n"]
    for c in crystals:
        narrative = c.get("narrative", "").strip()
        outcomes = c.get("key_outcomes") or []
        if not narrative and not outcomes:
            continue
        lines.append(f"- {narrative}")
        for o in outcomes[:3]:
            lines.append(f"  · {o}")

    return "\n".join(lines) if len(lines) > 1 else ""


def _format_lessons(agent_id: str, project_id: str | None) -> str:
    try:
        from hydrahive.tools._memory_store import load_filtered
        data = load_filtered(
            agent_id,
            filter_project="*",  # Lessons sind global relevant
            active_project=project_id,
            include_superseded=False,
        )
    except Exception as e:
        logger.debug("Crystal-Injection: load_filtered fehlgeschlagen: %s", e)
        return ""

    lessons = [
        (k, v) for k, v in data.items()
        if k.startswith("lesson.")
        and v.get("confidence", 0) >= _MIN_LESSON_CONFIDENCE
    ]

    if not lessons:
        return ""

    lessons.sort(key=lambda kv: kv[1].get("confidence", 0), reverse=True)
    lessons = lessons[:_MAX_LESSONS]

    lines: list[str] = ["### Lessons Learned\n"]
    for _, entry in lessons:
        content = entry.get("content", "").strip()
        if content:
            lines.append(f"- {content}")

    return "\n".join(lines) if len(lines) > 1 else ""
