"""Lehren mit Beleg im Runner (docs/specs/lehren-mit-beleg.md 10b + 10c).

- start_lessons: am Sitzungsende im Hintergrund auswerten (fire-and-forget wie die Compress-Pipeline).
- recall_lessons: vor der Arbeit passende Lehren holen – best-effort, ein Fehler liefert nur eine leere Liste.
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.db import errors_log

logger = logging.getLogger(__name__)


async def recall_lessons(agent_id: str, text: str, project_id: str | None) -> list[dict]:
    from hydrahive.lessons import recall
    try:
        return await recall.pick(agent_id, text, project_id=project_id)
    except Exception as e:  # noqa: BLE001 – Lehren sind Zugabe, der Lauf geht immer weiter
        logger.warning("Lehren-Abruf fehlgeschlagen (best-effort): %s", e)
        return []


async def _safe_lessons(agent_id: str, session_id: str) -> None:
    from hydrahive.lessons.extract import extract_session
    with errors_log.capture(source="runner.lessons_bg", session_id=session_id, agent_id=agent_id, reraise=False):
        await extract_session(agent_id, session_id)


def start_lessons(agent_id: str, session_id: str) -> asyncio.Task:
    return asyncio.create_task(_safe_lessons(agent_id, session_id), name=f"lessons-{session_id[:8]}")
