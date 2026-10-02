"""Abfragen für Buddys Web-Sitzungen (Spec docs/specs/buddy-session-picker.md).

Direkt per SQL gefiltert statt über ``sessions.list_for_user``: das liefert nur
die 50 zuletzt geänderten Sitzungen des Nutzers (Projekte, Automatik …) und
enthält auch Kanal-Sitzungen (WhatsApp, Discord, Matrix, Voice). Beides führte
dazu, dass Buddy die falsche oder keine Sitzung fand (F1/F2, 02.10.2026).
"""
from __future__ import annotations

import json

from hydrahive.db.connection import db
from hydrahive.db.sessions import Session

_WEB = "(channel IS NULL OR channel = '')"
_PREVIEW = 80
_SCAN = 40   # so viele frühe Nutzernachrichten werden nach echtem Text durchsucht


def newest_web(agent_id: str, user_id: str) -> Session | None:
    """Jüngste Web-Sitzung (nach Anlage) — die Sitzung von „Neuer Chat“."""
    with db() as conn:
        row = conn.execute(
            f"SELECT * FROM sessions WHERE agent_id = ? AND user_id = ? AND {_WEB} "
            "ORDER BY created_at DESC LIMIT 1",
            (agent_id, user_id),
        ).fetchone()
    return Session.from_row(row) if row else None


def get_web(agent_id: str, user_id: str, session_id: str) -> Session | None:
    """Die Sitzung, wenn sie eine Web-Sitzung dieses Buddy und Nutzers ist."""
    with db() as conn:
        row = conn.execute(
            f"SELECT * FROM sessions WHERE id = ? AND agent_id = ? AND user_id = ? AND {_WEB}",
            (session_id, agent_id, user_id),
        ).fetchone()
    return Session.from_row(row) if row else None


def list_web(agent_id: str, user_id: str, *, offset: int, limit: int) -> tuple[list[dict], bool]:
    """Web-Sitzungen, zuletzt geänderte zuerst, mit Vorschau und Anzahl."""
    with db() as conn:
        rows = conn.execute(
            f"SELECT s.*, (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS n "
            f"FROM sessions s WHERE s.agent_id = ? AND s.user_id = ? AND {_WEB} "
            "ORDER BY s.updated_at DESC, s.created_at DESC LIMIT ? OFFSET ?",
            (agent_id, user_id, limit + 1, offset),
        ).fetchall()
        items = [{
            "id": r["id"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "project_id": r["project_id"],
            "message_count": r["n"],
            "first_message": _first_message(conn, r["id"]),
        } for r in rows[:limit]]
    return items, len(rows) > limit


def _first_message(conn, session_id: str) -> str | None:
    rows = conn.execute(
        "SELECT content FROM messages WHERE session_id = ? AND role = 'user' "
        "ORDER BY created_at ASC LIMIT ?",
        (session_id, _SCAN),
    ).fetchall()
    for row in rows:
        text = preview(row["content"])
        if text:
            return text
    return None


def preview(raw: str | None) -> str | None:
    """Text einer Nutzernachricht für die Vorschau: Befehle und Werkzeug-
    Ergebnisse überspringen, Leerraum vereinheitlichen, auf 80 Zeichen kürzen."""
    text = _text_of(raw)
    if not text or text.startswith("/"):
        return None
    text = " ".join(text.split())
    return text if len(text) <= _PREVIEW else text[: _PREVIEW - 1] + "…"


def _text_of(raw: str | None) -> str:
    if not raw:
        return ""
    if not raw.lstrip().startswith("["):
        return raw.strip()
    try:
        blocks = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw.strip()
    if not isinstance(blocks, list):
        return ""
    parts = [b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"]
    return " ".join(p for p in parts if isinstance(p, str)).strip()
