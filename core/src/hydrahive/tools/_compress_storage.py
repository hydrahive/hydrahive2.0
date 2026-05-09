"""Compress-Pipeline — File-IO für CompressedObservations (JSONL pro Session)."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

CompressedObservation = dict[str, Any]


def _compressed_file(agent_id: str, session_id: str) -> Path:
    return settings.agents_dir / agent_id / "compressed" / f"{session_id}.jsonl"


def save_compressed(agent_id: str, session_id: str, obs: CompressedObservation) -> None:
    path = _compressed_file(agent_id, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obs, ensure_ascii=False) + "\n")


def load_compressed(
    agent_id: str,
    session_id: str,
) -> list[CompressedObservation]:
    """Lädt alle CompressedObservations einer Session."""
    path = _compressed_file(agent_id, session_id)
    if not path.exists():
        return []
    result: list[CompressedObservation] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return result
