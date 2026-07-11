"""Persistenter Projekt-Arbeitszustand über Compactions und Sessions hinweg."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from hydrahive.compaction.redact import redact
from hydrahive.compaction.serialize import serialize_for_summary
from hydrahive.compaction.summarize import summarize
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.projects._paths import ensure_workspace

HANDOVER_RELATIVE_PATH = Path(".hydrahive/HANDOVER.md")


def path_for_project(project_id: str) -> Path:
    return ensure_workspace(project_id) / HANDOVER_RELATIVE_PATH


def write_project_handover(project_id: str, *, session_id: str, agent_id: str, summary: str) -> Path:
    """Schreibt redigiert und atomar; der Zielpfad wird allein aus project_id abgeleitet."""
    target = path_for_project(project_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = redact(
        "# Projekt-Handover\n\n"
        f"- Projekt-ID: `{project_id}`\n"
        f"- Quell-Session: `{session_id}`\n"
        f"- Agent-ID: `{agent_id}`\n"
        f"- Aktualisiert: `{datetime.now(timezone.utc).isoformat()}`\n\n"
        "Diese Übergabe ist Arbeitskontext aus der vorherigen Session. "
        "Prüfe Datei- und Git-Zustand, bevor du Änderungen vornimmst.\n\n"
        f"{summary.strip()}\n"
    )
    tmp = target.with_suffix(f".tmp-{os.getpid()}")
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, target)
    return target


def read_project_handover(project_id: str) -> str | None:
    path = path_for_project(project_id)
    try:
        text = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return text or None


def prompt_for_new_session(session_id: str) -> str | None:
    """Nur eine noch leere Projekt-Session bekommt die Übergabe als Startkontext."""
    session = sessions_db.get(session_id)
    if not session or not session.project_id or messages_db.list_for_session(session_id, limit=1):
        return None
    text = read_project_handover(session.project_id)
    if not text:
        return None
    return "[Projekt-Handover aus der vorherigen Session]\n" + text


async def create_for_session(session_id: str, *, model: str, tool_result_limit: int | None = None) -> Path | None:
    """Erzeugt eine hochwertige Übergabe aus dem vollständigen sichtbaren Verlauf."""
    session = sessions_db.get(session_id)
    if not session or not session.project_id:
        return None
    history = messages_db.list_for_llm(session_id)
    if not history:
        return None
    kwargs = {} if tool_result_limit is None else {"tool_result_limit": tool_result_limit}
    summary = await summarize(
        model=model,
        serialized_history=serialize_for_summary(history, **kwargs),
        previous_summary=messages_db.get_latest_summary(session_id),
    )
    return write_project_handover(
        session.project_id, session_id=session.id, agent_id=session.agent_id, summary=summary,
    )
