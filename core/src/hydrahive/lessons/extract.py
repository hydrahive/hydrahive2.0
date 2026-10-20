"""Eine abgeschlossene Sitzung auswerten (Spec 10b): Modell wählen → Auftrag → prüfen → höchstens eine Lehre speichern.

Ergebnis (für Log und Tests): {"status": "saved"|"no_entry"|"rejected"|"skipped_done"|"skipped_running"|"skipped_short"|
"off"|"error", …}. Unlesbare Antwort und Fehler beim Modell markieren die Sitzung NICHT als erledigt – nächstes Mal neu.
Läuft eine Sitzung weiter, wird sie nach jeweils AGAIN_AFTER neuen Nachrichten erneut ausgewertet (ohne sich selbst zu
bestärken – store.add zählt dieselbe Sitzung nur einmal). Je Sitzung läuft höchstens eine Auswertung zugleich.
"""
from __future__ import annotations

import logging

from hydrahive.lessons import model, prompt, store

logger = logging.getLogger(__name__)

MIN_MESSAGES = 10
AGAIN_AFTER = 10
MAX_TOKENS = 3000
_running: set[tuple[str, str]] = set()


def _messages(session_id: str):
    from hydrahive.db import messages
    return messages.list_for_session(session_id)


async def _complete(msgs: list[dict], model: str | None = None, temperature: float = 0.2, max_tokens: int = MAX_TOKENS) -> str:
    from hydrahive.llm import client
    return await client.complete(msgs, model=model, temperature=temperature, max_tokens=max_tokens)


def _model() -> str:
    from hydrahive.llm._config import resolve_lessons_model
    return resolve_lessons_model()


def _scope(agent_id: str, session_id: str) -> str:
    """Projekt der Sitzung, sonst nur dieser Agent (Spec 10, Entscheidung 3)."""
    from hydrahive.db import sessions
    session = sessions.get(session_id)
    return f"project:{session.project_id}" if session and session.project_id else "agent"


async def extract_session(agent_id: str, session_id: str) -> dict:
    llm = _model()
    if not llm:
        return {"status": "off"}
    job = (agent_id, session_id)
    if job in _running:
        return {"status": "skipped_running"}
    _running.add(job)
    try:
        return await _extract(agent_id, session_id, llm)
    finally:
        _running.discard(job)


async def _extract(agent_id: str, session_id: str, llm: str) -> dict:
    msgs = _messages(session_id)
    seen = store.done_count(agent_id, session_id)
    if seen is not None and len(msgs) < seen + AGAIN_AFTER:
        return {"status": "skipped_done"}
    if len(msgs) < MIN_MESSAGES:
        return {"status": "skipped_short"}
    rec = prompt.record(msgs)
    try:
        raw = await _complete(prompt.messages(rec), model=llm)
    except Exception as e:  # noqa: BLE001 – Modell weg darf nie den Runner stören; nächstes Mal neu
        logger.warning("lessons: Modell-Fehler bei %s/%s: %s", agent_id, session_id, e)
        return {"status": "error"}
    answer = prompt.parse(raw)
    if answer is None:
        logger.info("lessons: unlesbare Antwort bei %s/%s", agent_id, session_id)
        return {"status": "rejected", "reason": "unreadable"}
    lesson, reason = model.check(answer, rec)
    store.mark_done(agent_id, session_id, len(msgs))
    if reason == "no_entry":
        return {"status": "no_entry"}
    if lesson is None:
        logger.info("lessons: Lehre verworfen (%s) bei %s/%s", reason, agent_id, session_id)
        return {"status": "rejected", "reason": reason}
    saved = store.add(agent_id, {**lesson, "session_id": session_id}, scope=_scope(agent_id, session_id))
    logger.info("lessons: %s aus %s/%s (%s)", saved["id"], agent_id, session_id, saved["scope"])
    return {"status": "saved", "lesson": saved}
