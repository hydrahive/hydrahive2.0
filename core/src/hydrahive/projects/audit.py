"""Audit-Log pro Projekt (#74): wer hat wann was geändert.

Append-only. Die einzige Schreib-/Lese-Senke für `project_audit_log`. Aufrufer
sind die Projekt-Route-Handler (dort ist der handelnde User = auth[0] bekannt).
`log()` darf die Hauptoperation NIE brechen — Fehler werden geloggt, nicht geworfen.
"""
from __future__ import annotations

import json
import logging

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

logger = logging.getLogger(__name__)


def log(
    project_id: str,
    user_id: str,
    action: str,
    target: str | None = None,
    details: dict | None = None,
) -> None:
    """Schreibt einen Audit-Eintrag. Schluckt Fehler (mit Logging) — Audit darf
    die eigentliche Projekt-Operation nicht zum Scheitern bringen."""
    try:
        details_json = json.dumps(details, ensure_ascii=False) if details is not None else None
        with db() as conn:
            conn.execute(
                """INSERT INTO project_audit_log
                   (id, project_id, user_id, action, target, details_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (uuid7(), project_id, user_id, action, target, details_json, now_iso()),
            )
    except Exception:
        logger.warning(
            "project audit: Eintrag fehlgeschlagen (project=%s action=%s)",
            project_id, action, exc_info=True,
        )


def list_for_project(
    project_id: str,
    action: str | None = None,
    user_id: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """Audit-Einträge eines Projekts, neueste zuerst, optional gefiltert."""
    clauses = ["project_id = ?"]
    params: list = [project_id]
    if action:
        clauses.append("action = ?")
        params.append(action)
    if user_id:
        clauses.append("user_id = ?")
        params.append(user_id)
    params.append(limit)
    where = " AND ".join(clauses)
    with db() as conn:
        rows = conn.execute(
            f"""SELECT id, project_id, user_id, action, target, details_json, created_at
                FROM project_audit_log WHERE {where}
                ORDER BY created_at DESC, id DESC LIMIT ?""",
            params,
        ).fetchall()
    return [
        {
            "id": r["id"],
            "project_id": r["project_id"],
            "user": r["user_id"],
            "action": r["action"],
            "target": r["target"],
            "details": json.loads(r["details_json"]) if r["details_json"] else None,
            "created_at": r["created_at"],
        }
        for r in rows
    ]
