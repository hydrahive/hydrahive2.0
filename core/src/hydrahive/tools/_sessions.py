from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hydrahive.settings import settings

# ---------------------------------------------------------------------------
# Typen
# ---------------------------------------------------------------------------

Session = dict[str, Any]

_STATUS_ACTIVE = "active"
_STATUS_COMPLETED = "completed"
_STATUS_ABANDONED = "abandoned"
# "paused" = Runner-Abbruch durch max_iterations. Resumable per User-Klick auf
# "Weitermachen" — Backend startet runner.run mit derselben session_id, History
# bleibt erhalten. Im Gegensatz zu "abandoned" (echter Error wie max_tokens,
# Loop, LLM-API-Fehler) ist das kein Endzustand.
_STATUS_PAUSED = "paused"


# ---------------------------------------------------------------------------
# Storage-Helpers
# ---------------------------------------------------------------------------

def _sessions_dir(agent_id: str) -> Path:
    """Eigenes Verzeichnis für Sessions — getrennt von memory.json."""
    return settings.agents_dir / agent_id / "sessions"


def _session_file(agent_id: str, session_id: str) -> Path:
    return _sessions_dir(agent_id) / f"{session_id}.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_session_file(path: Path) -> Session | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _save_session_file(path: Path, session: Session) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

def session_start(
    agent_id: str,
    session_id: str,
    *,
    project: str | None = None,
    model: str | None = None,
    first_prompt: str | None = None,
) -> Session:
    """
    Erstellt oder aktualisiert eine Session.
    Idempotent — mehrfaches Aufrufen mit derselben session_id ist sicher.
    """
    path = _session_file(agent_id, session_id)
    existing = _load_session_file(path)
    if existing and existing.get("status") == _STATUS_ACTIVE:
        return existing

    session: Session = {
        "id": session_id,
        "agent_id": agent_id,
        "project": project,
        "started_at": _now_iso(),
        "ended_at": None,
        "status": _STATUS_ACTIVE,
        "observation_count": 0,
        "model": model,
        "first_prompt": first_prompt[:500] if first_prompt else None,
        "summary": None,
    }
    _save_session_file(path, session)
    return session


def session_end(
    agent_id: str,
    session_id: str,
    *,
    status: str = _STATUS_COMPLETED,
    summary: str | None = None,
) -> Session | None:
    """
    Beendet eine Session. Setzt ended_at und status.
    Gibt None zurück wenn Session nicht gefunden.
    """
    # Live-Aktivität (Pixel-Leiste) unbedingt abräumen — auch wenn die Session-
    # Datei fehlt/schon beendet ist. Lazy-Import gegen Import-Zyklus.
    from hydrahive.runner import activity
    activity.stop(session_id)

    path = _session_file(agent_id, session_id)
    session = _load_session_file(path)
    if session is None:
        return None
    if session.get("status") != _STATUS_ACTIVE:
        return session  # bereits beendet — nicht überschreiben

    session["ended_at"] = _now_iso()
    session["status"] = status if status in (_STATUS_COMPLETED, _STATUS_ABANDONED, _STATUS_PAUSED) else _STATUS_COMPLETED
    if summary is not None:
        session["summary"] = summary

    _save_session_file(path, session)
    return session


def session_get(agent_id: str, session_id: str) -> Session | None:
    """Lädt eine Session. Gibt None zurück wenn nicht vorhanden."""
    return _load_session_file(_session_file(agent_id, session_id))


def session_increment_observations(agent_id: str, session_id: str) -> None:
    """Erhöht observation_count um 1. Fire-and-forget — ignoriert Fehler."""
    path = _session_file(agent_id, session_id)
    session = _load_session_file(path)
    if session is None:
        return
    session["observation_count"] = session.get("observation_count", 0) + 1
    _save_session_file(path, session)


def session_list(
    agent_id: str,
    *,
    project: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[Session]:
    """
    Listet Sessions eines Agents. Optional nach project und status gefiltert.
    Sortiert nach started_at descending (neueste zuerst).

    Known Limitation: glob() lädt alle Session-Dateien bevor limit greift.
    Bei sehr vielen Sessions (10k+) steigt der Speicherbedarf linear.
    Für den aktuellen Scope (< 1000 Sessions pro Agent) kein Problem.
    """
    sessions_dir = _sessions_dir(agent_id)
    if not sessions_dir.exists():
        return []

    sessions: list[Session] = []
    for path in sessions_dir.glob("*.json"):
        s = _load_session_file(path)
        if s is None:
            continue
        if project is not None and s.get("project") != project:
            continue
        if status is not None and s.get("status") != status:
            continue
        sessions.append(s)

    sessions.sort(key=lambda s: s.get("started_at") or "", reverse=True)
    return sessions[:limit]
