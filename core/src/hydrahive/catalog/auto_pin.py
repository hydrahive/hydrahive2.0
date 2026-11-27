"""Automatisch anheften (Bereiche Spec 4.5, AB6): die meistbenutzten ``run_tool``-Tools eines Agenten.

Quelle ist ``catalog_events`` (kind ``run``), verbunden über die Sitzung (``sessions.agent_id``). Gewertet werden die
neuesten ``MAX_EVENTS`` Ereignisse der letzten ``AUTO_PIN_DAYS`` Tage. Es kommen nur Tools in Frage, die der Lauf wirksam
hat (``effective``) und weder zum festen Kern noch zu den Katalog-Werkzeugen gehören (die sind ohnehin sichtbar).

Harte Regel: Der Runner ruft das EINMAL beim Laufstart auf (wie ``remembered_for``). Ein Ereignis während des Laufs ändert
die Tool-Liste nie – sonst bräche der Prompt-Cache. ``auto_pinned`` wirft nie; bei Fehlern kommt ``[]`` und eine Warnung.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from hydrahive.catalog import CATALOG_TOOLS
from hydrahive.db.connection import db

logger = logging.getLogger(__name__)

AUTO_PIN_MAX = 8
AUTO_PIN_DAYS = 30
MAX_EVENTS = 500


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _since_iso() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=AUTO_PIN_DAYS)).isoformat(timespec="milliseconds")


def auto_pinned(agent_id: str, effective: list[str]) -> list[str]:
    """Bis zu ``AUTO_PIN_MAX`` Tool-Namen, sortiert nach Häufigkeit (absteigend), dann nach Name. Wirft nie."""
    if not agent_id or not effective:
        return []
    try:
        from hydrahive.runner._catalog_mode import CORE_TOOLS
        with db() as conn:
            rows = conn.execute(
                "SELECT e.tool FROM catalog_events e JOIN sessions s ON s.id = e.session_id "
                "WHERE s.agent_id = ? AND e.kind = 'run' AND e.tool != '' AND e.created_at >= ? "
                "ORDER BY e.id DESC LIMIT ?", (agent_id, _since_iso(), MAX_EVENTS)).fetchall()
        allowed = set(effective) - set(CORE_TOOLS) - CATALOG_TOOLS
        counts = Counter(r["tool"] for r in rows if r["tool"] in allowed)
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [name for name, _ in ranked[:AUTO_PIN_MAX]]
    except Exception:  # noqa: BLE001 — das Anheften darf nie einen Lauf stören
        logger.warning("Auto-Anheften fehlgeschlagen (Agent %s)", agent_id, exc_info=True)
        return []
