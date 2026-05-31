"""Scratchpad-Service: zwei physisch getrennte Zonen pro User.

user.md  — nur der Mensch (via Web-Konsole)
agent.md — nur der Agent (via write_scratchpad-Tool)

Die Trennung in zwei Dateien macht es technisch unmöglich, dass der Agent
Tills Text überschreibt. Speicher: data_dir/scratchpad/<user_id>/{user,agent}.md
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

MAX_ZONE_BYTES = 256 * 1024  # 256 KB pro Zone


class ScratchpadTooLarge(ValueError):
    """Zone-Inhalt überschreitet MAX_ZONE_BYTES."""


def _zone_path(user_id: str, zone: str) -> Path:
    return settings.data_dir / "scratchpad" / user_id / f"{zone}.md"


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("scratchpad: konnte %s nicht lesen", path)
        return ""


def _write_atomic(path: Path, content: str) -> None:
    if len(content.encode("utf-8")) > MAX_ZONE_BYTES:
        raise ScratchpadTooLarge(f"Scratchpad-Zone überschreitet {MAX_ZONE_BYTES} Bytes")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def get_user(user_id: str) -> str:
    return _read(_zone_path(user_id, "user"))


def save_user(user_id: str, content: str) -> None:
    _write_atomic(_zone_path(user_id, "user"), content)


def get_agent(user_id: str) -> str:
    return _read(_zone_path(user_id, "agent"))


def save_agent(user_id: str, content: str) -> None:
    _write_atomic(_zone_path(user_id, "agent"), content)


def clear_agent(user_id: str) -> None:
    path = _zone_path(user_id, "agent")
    if path.exists():
        path.unlink()


def get_combined(user_id: str) -> str:
    """Beide Zonen klar beschriftet — Format das der Agent via read_scratchpad sieht."""
    user = get_user(user_id).strip() or "_(leer)_"
    agent = get_agent(user_id).strip() or "_(leer)_"
    return f"## Tills Ideen\n\n{user}\n\n## Agent-Notizen (dein Bereich)\n\n{agent}"
