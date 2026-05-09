"""Crystal-Kontext-Injection: vergangene Sessions in den System-Prompt einweben.

Lädt beim Session-Start:
  - Letzte N Crystals (Narrative + Key Outcomes)
  - Lessons (lesson.*-Keys mit confidence >= threshold), sortiert nach Confidence

Gibt einen kompakten Markdown-Block zurück, oder None wenn nichts vorhanden.
Kein LLM-Call — rein deterministisch aus gespeicherten Daten.

Per-Agent-Overrides via agent_config (#115/#113):
  - memory_max_crystals, memory_max_lessons, memory_min_lesson_confidence,
    memory_max_chars
  - memory_crystal_scope: "project_and_global" (Default) oder "project_only"
"""
from __future__ import annotations

import logging
from typing import Any

from hydrahive.agents._defaults import (
    DEFAULT_MEMORY_CRYSTAL_SCOPE,
    DEFAULT_MEMORY_MAX_CHARS,
    DEFAULT_MEMORY_MAX_CRYSTALS,
    DEFAULT_MEMORY_MAX_LESSONS,
    DEFAULT_MEMORY_MIN_LESSON_CONFIDENCE,
)

logger = logging.getLogger(__name__)


def _resolve_config(agent_config: dict[str, Any] | None) -> dict[str, Any]:
    """Liest Memory-Override-Felder aus agent_config oder fällt auf Defaults zurück."""
    cfg = agent_config or {}
    return {
        "max_crystals": int(cfg.get("memory_max_crystals", DEFAULT_MEMORY_MAX_CRYSTALS)),
        "max_lessons": int(cfg.get("memory_max_lessons", DEFAULT_MEMORY_MAX_LESSONS)),
        "min_lesson_confidence": float(
            cfg.get("memory_min_lesson_confidence", DEFAULT_MEMORY_MIN_LESSON_CONFIDENCE)
        ),
        "max_chars": int(cfg.get("memory_max_chars", DEFAULT_MEMORY_MAX_CHARS)),
        "crystal_scope": str(cfg.get("memory_crystal_scope", DEFAULT_MEMORY_CRYSTAL_SCOPE)),
    }


def build_memory_context(
    agent_id: str,
    project_id: str | None = None,
    *,
    agent_config: dict[str, Any] | None = None,
) -> str | None:
    """
    Baut den Memory-Kontext-Block für den System-Prompt.
    Gibt None zurück wenn weder Crystals noch Lessons vorhanden — oder wenn
    alle Limits auf 0 stehen (Specialist mit deaktiviertem Memory).
    """
    cfg = _resolve_config(agent_config)
    if cfg["max_crystals"] <= 0 and cfg["max_lessons"] <= 0:
        return None

    crystals_text = _format_crystals(agent_id, project_id, cfg)
    lessons_text = _format_lessons(agent_id, project_id, cfg)

    if not crystals_text and not lessons_text:
        return None

    parts: list[str] = ["## Memory — What I've learned in past sessions\n"]
    if crystals_text:
        parts.append(crystals_text)
    if lessons_text:
        parts.append(lessons_text)

    block = "\n".join(parts)

    max_chars = cfg["max_chars"]
    if max_chars > 0 and len(block) > max_chars:
        block = block[:max_chars] + f"\n[... {len(block) - max_chars} chars truncated]"

    return block


def _format_crystals(agent_id: str, project_id: str | None, cfg: dict[str, Any]) -> str:
    if cfg["max_crystals"] <= 0:
        return ""
    include_global = cfg["crystal_scope"] == "project_and_global"
    try:
        from hydrahive.tools._crystallize import list_crystals
        crystals = list_crystals(
            agent_id,
            project=project_id,
            limit=cfg["max_crystals"],
            include_global=include_global,
        )
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


def _format_lessons(agent_id: str, project_id: str | None, cfg: dict[str, Any]) -> str:
    if cfg["max_lessons"] <= 0:
        return ""
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

    threshold = cfg["min_lesson_confidence"]
    lessons = [
        (k, v) for k, v in data.items()
        if k.startswith("lesson.")
        and v.get("confidence", 0) >= threshold
    ]

    if not lessons:
        return ""

    lessons.sort(key=lambda kv: kv[1].get("confidence", 0), reverse=True)
    lessons = lessons[:cfg["max_lessons"]]

    lines: list[str] = ["### Lessons Learned\n"]
    for _, entry in lessons:
        content = entry.get("content", "").strip()
        if content:
            lines.append(f"- {content}")

    return "\n".join(lines) if len(lines) > 1 else ""
