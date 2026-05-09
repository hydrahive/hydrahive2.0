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


def list_crystals(
    agent_id: str,
    project: str | None = None,
    limit: int = 20,
) -> list[Crystal]:
    """Lädt Crystals eines Agents. Optional nach project gefiltert, neueste zuerst."""
    path = _crystals_file(agent_id)
    if not path.exists():
        return []

    results: list[Crystal] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if project is not None and entry.get("project") != project:
                continue
            results.append(entry)
    except OSError:
        return []

    # Neueste zuerst, dann limit anwenden
    results.reverse()
    return results[:limit]


def get_crystal(agent_id: str, session_id: str) -> Crystal | None:
    """Gibt den Crystal einer bestimmten Session zurück (oder None)."""
    path = _crystals_file(agent_id)
    if not path.exists():
        return None
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("session_id") == session_id:
                    return entry
            except json.JSONDecodeError:
                continue
    except OSError:
        return None
    return None
