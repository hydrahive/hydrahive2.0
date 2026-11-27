"""Aufräumen der Pool-Tabellen beim Löschen von Agent, Projekt oder Nutzer (abgespalten aus ``tool_pools.py``).

Fehler hier dürfen das Löschen nie verhindern.
"""
from __future__ import annotations

import logging

from hydrahive.db.connection import db

logger = logging.getLogger(__name__)


def remove_agent(agent_id: str) -> None:
    """Beim Löschen eines Agenten: Pool aufräumen (Fehler hier dürfen das Löschen nie verhindern)."""
    try:
        with db() as conn:
            conn.execute("DELETE FROM agent_tool_pools WHERE agent_id = ?", (agent_id,))
    except Exception:  # noqa: BLE001
        logger.warning("Pool von Agent %s nicht aufgeräumt", agent_id, exc_info=True)


def remove_project(project_id: str) -> None:
    try:
        with db() as conn:
            conn.execute("DELETE FROM project_tool_pools WHERE project_id = ?", (project_id,))
    except Exception:  # noqa: BLE001
        logger.warning("Pool von Projekt %s nicht aufgeräumt", project_id, exc_info=True)


def remove_user(username: str) -> None:
    """Beim Löschen eines Nutzers: Besitzer-Freigabe entfernen (Buddy-Review #786) – sonst erbt ein später gleichnamig
    angelegter Nutzer die alten Freigaben. Fehler dürfen das Löschen nie verhindern."""
    try:
        with db() as conn:
            conn.execute("DELETE FROM owner_tool_grants WHERE username = ?", (username,))
    except Exception:  # noqa: BLE001
        logger.warning("Besitzer-Freigabe von %s nicht aufgeräumt", username, exc_info=True)
