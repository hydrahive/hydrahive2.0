"""Crystallize-Pipeline — Storage für Crystals (JSONL pro Agent)."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from hydrahive.settings import settings

logger = logging.getLogger(__name__)


Crystal = dict[str, Any]


def _crystals_file(agent_id: str) -> Path:
    """Alle Crystals eines Agents in einer JSONL-Datei."""
    return settings.agents_dir / agent_id / "crystals.jsonl"


def save_crystal(agent_id: str, crystal: Crystal) -> None:
    """Speichert einen Crystal append-only in crystals.jsonl."""
    path = _crystals_file(agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(crystal, ensure_ascii=False) + "\n")


def _iter_entries(agent_id: str):
    """Yields parsed JSONL entries in file-order, skipping broken lines."""
    path = _crystals_file(agent_id)
    if not path.exists():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def list_crystals(
    agent_id: str,
    project: str | None = None,
    limit: int = 20,
    include_global: bool = False,
) -> list[Crystal]:
    """Lädt Crystals eines Agents. Optional nach project gefiltert, neueste zuerst.

    Bei mehreren Crystals derselben Session (Re-Crystallize) wird nur die
    neueste Version zurückgegeben — die jsonl ist append-only versioniert.

    project=None: kein Filter (alle Crystals sichtbar).
    project=<id>, include_global=False: nur Crystals dieses Projekts.
    project=<id>, include_global=True: Crystals dieses Projekts + globale (project=None).
    """
    by_session: dict[str, Crystal] = {}
    for entry in _iter_entries(agent_id):
        if project is not None:
            entry_project = entry.get("project")
            if entry_project != project and not (include_global and entry_project is None):
                continue
        sid = entry.get("session_id")
        if sid is None:
            continue
        by_session[sid] = entry  # last write wins (jsonl is append-order = chrono)

    results = list(by_session.values())
    results.reverse()  # newest first
    return results[:limit]


def get_crystal(agent_id: str, session_id: str) -> Crystal | None:
    """Gibt den neuesten Crystal einer Session zurück (oder None).

    Append-only versioniert: bei mehreren Einträgen mit gleicher session_id
    gewinnt der zuletzt geschriebene.
    """
    latest: Crystal | None = None
    for entry in _iter_entries(agent_id):
        if entry.get("session_id") == session_id:
            latest = entry
    return latest
