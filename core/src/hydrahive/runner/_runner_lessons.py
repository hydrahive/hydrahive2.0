"""Lehren mit Beleg am Sitzungsende im Hintergrund anstoßen (docs/specs/lehren-mit-beleg.md 10b).

Fire-and-forget wie die Compress-Pipeline: blockiert `Done` nicht, Fehler landen in errors_log statt still zu verschwinden.
"""
from __future__ import annotations

import asyncio

from hydrahive.db import errors_log


async def _safe_lessons(agent_id: str, session_id: str) -> None:
    from hydrahive.lessons.extract import extract_session
    with errors_log.capture(source="runner.lessons_bg", session_id=session_id, agent_id=agent_id, reraise=False):
        await extract_session(agent_id, session_id)


def start_lessons(agent_id: str, session_id: str) -> asyncio.Task:
    return asyncio.create_task(_safe_lessons(agent_id, session_id), name=f"lessons-{session_id[:8]}")
