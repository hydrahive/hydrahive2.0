"""Messung des Tool-Katalogs je Sitzung (Spec V7/K8): gesucht, gefunden, benutzt, „gesucht, nichts benutzt“.

Ereignisse: ``record_search`` (find_tools/find_skills nach der Suche) und ``record_run`` (run_tool erfolgreich ausgeführt, im
Runner). Schreiben ist best effort: jeder Fehler wird geschluckt und geloggt und stört nie einen Lauf. Gespeichert werden nur
Anfragetext (begrenzt) und Namen, nie Argumente oder Ergebnisse der Tools.

„Gesucht, nichts benutzt“: Nach einer Tool-Suche wurde keiner ihrer Treffer später in derselben Sitzung per run_tool
erfolgreich benutzt. Skill-Suchen werden nur gezählt (die Benutzung eines Skills ist nicht erfasst, ``used`` ist dort None).
"""
from __future__ import annotations

import json
import logging

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

logger = logging.getLogger(__name__)

KINDS = ("search_tools", "search_skills", "run")
MAX_QUERY = 500
MAX_RESULTS = 50
MAX_EVENTS = 1000


def _insert(session_id: str, kind: str, query: str, results: list[str], tool: str) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO catalog_events(session_id, kind, query, results, tool, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, kind, query, json.dumps(results, ensure_ascii=False), tool, now_iso()))


def record_search(session_id: str | None, kind: str, query: str, results: list[str]) -> None:
    """Eine Suche festhalten (kind: search_tools | search_skills). Wirft nie."""
    if not session_id or kind not in ("search_tools", "search_skills"):
        return
    try:
        _insert(session_id, kind, (query or "")[:MAX_QUERY], [str(r) for r in results][:MAX_RESULTS], "")
    except Exception:  # noqa: BLE001 — die Messung darf nie einen Lauf stören
        logger.warning("Katalog-Messung: Suche nicht gespeichert", exc_info=True)


def record_run(session_id: str | None, tool: str) -> None:
    """Ein erfolgreich per run_tool benutztes Tool festhalten. Wirft nie."""
    if not session_id or not tool:
        return
    try:
        _insert(session_id, "run", "", [], str(tool)[:200])
    except Exception:  # noqa: BLE001
        logger.warning("Katalog-Messung: Benutzung nicht gespeichert", exc_info=True)


def _load(session_id: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id, kind, query, results, tool, created_at FROM catalog_events WHERE session_id = ? "
            "ORDER BY id LIMIT ?", (session_id, MAX_EVENTS)).fetchall()
    out = []
    for r in rows:
        try:
            results = json.loads(r["results"]) if r["results"] else []
        except (json.JSONDecodeError, TypeError):
            results = []
        out.append({"id": r["id"], "kind": r["kind"], "query": r["query"], "results": results, "tool": r["tool"],
                    "created_at": r["created_at"]})
    return out


def summary(session_id: str) -> dict:
    """Zusammenfassung einer Sitzung: Zähler, gefundene und benutzte Namen, Ereignisliste, nie benutzte Suchen."""
    try:
        raw = _load(session_id)
    except Exception:  # noqa: BLE001 — Tabelle fehlt o. Ä.: leere Messung statt Fehler
        logger.warning("Katalog-Messung nicht lesbar", exc_info=True)
        raw = []
    events: list[dict] = []
    found: list[str] = []
    used: list[str] = []
    for i, ev in enumerate(raw):
        if ev["kind"] == "run":
            if ev["tool"] not in used:
                used.append(ev["tool"])
            continue
        for name in ev["results"]:
            if name not in found:
                found.append(name)
        later = {e["tool"] for e in raw[i + 1:] if e["kind"] == "run"}
        hit = None if ev["kind"] == "search_skills" else bool(later & set(ev["results"]))
        events.append({"kind": ev["kind"], "query": ev["query"], "results": ev["results"], "used": hit,
                       "created_at": ev["created_at"]})
    tool_searches = [e for e in events if e["kind"] == "search_tools"]
    unused = [e["query"] for e in tool_searches if e["used"] is False]
    return {
        "session_id": session_id,
        "searches": len(events),
        "tool_searches": len(tool_searches),
        "skill_searches": len(events) - len(tool_searches),
        "searches_unused": len(unused),
        "unused_queries": unused,
        "found": found,
        "used": used,
        "events": events,
    }
