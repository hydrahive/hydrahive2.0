"""Eine abgeschlossene Sitzung auswerten (Spec 10b): Modell wählen → Auftrag → prüfen → höchstens eine Lehre speichern.

Ergebnis (für Log und Tests): {"status": "saved"|"no_entry"|"rejected"|"skipped_done"|"skipped_running"|"skipped_short"|
"off"|"error", …}. Unlesbare Antwort und Fehler beim Modell markieren die Sitzung NICHT als erledigt – nächstes Mal neu.
Läuft eine Sitzung weiter, wird sie nach jeweils AGAIN_AFTER neuen Nachrichten erneut ausgewertet (ohne sich selbst zu
bestärken – store.add zählt dieselbe Sitzung nur einmal). Je Sitzung läuft höchstens eine Auswertung zugleich.
"""
from __future__ import annotations

import logging

import asyncio

from hydrahive.lessons import check, model, prompt, store

logger = logging.getLogger(__name__)

MIN_MESSAGES = 10
AGAIN_AFTER = 10
CONTEXT = 4                # beim erneuten Auswerten: so viele Nachrichten vor dem neuen Teil als Zusammenhang
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


def since(msgs: list, seen: int | None) -> list:
    """Spec 10d: nur der seit der letzten Auswertung neue Teil, plus CONTEXT Nachrichten davor."""
    if not seen:
        return msgs
    return msgs[max(0, seen - CONTEXT):]


async def _counter_check(agent_id: str, session_id: str, lesson: dict, rec: str, llm: str) -> str:
    """Spec 10d: "" = belegt, "not_supported" = abgelehnt, "check_unreadable"/"error" = später neu versuchen."""
    try:
        raw = await asyncio.wait_for(_complete(check.messages(lesson, check.window(rec, lesson["quote"])), model=llm,
                                               temperature=0.0, max_tokens=300), timeout=check.TIMEOUT)
    except Exception as e:  # noqa: BLE001 – auch Zeitüberschreitung
        logger.warning("lessons: Gegenprüfung fehlgeschlagen bei %s/%s: %s", agent_id, session_id, e)
        return "error"
    ok = check.verdict(raw)
    if ok is None:
        return "check_unreadable"
    if not ok:
        logger.info("lessons: Gegenprüfung lehnt ab bei %s/%s: %s", agent_id, session_id, (raw or "")[:200])
    return "" if ok else "not_supported"


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
    rec = prompt.record(since(msgs, seen))
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
    if lesson is not None:
        reason = await _counter_check(agent_id, session_id, lesson, rec, llm)
        if reason in ("error", "check_unreadable"):              # nicht als erledigt markieren – nächstes Mal neu
            return {"status": "error"} if reason == "error" else {"status": "rejected", "reason": reason}
    store.mark_done(agent_id, session_id, len(msgs))
    if reason == "no_entry":
        return {"status": "no_entry"}
    if reason:
        logger.info("lessons: Lehre verworfen (%s) bei %s/%s", reason, agent_id, session_id)
        return {"status": "rejected", "reason": reason}
    saved = store.add(agent_id, {**lesson, "session_id": session_id}, scope=_scope(agent_id, session_id))
    logger.info("lessons: %s aus %s/%s (%s)", saved["id"], agent_id, session_id, saved["scope"])
    return {"status": "saved", "lesson": saved}
