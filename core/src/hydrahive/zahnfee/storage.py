"""Zahnfee-Briefing pro Nutzer — HH_DATA_DIR/zahnfee/<user>.json.

Früher eine globale Datei (zahnfee_briefing.json) mit den Aktivitäten aller
Nutzer, lesbar für jeden Login. Die Altdatei wird nicht mehr gelesen.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class Briefing:
    generated_at: str
    date: str
    open_items: str
    went_well: str
    went_badly: str
    today: str
    error: str | None = None


def _path(username: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", username) or "_"
    return settings.data_dir / "zahnfee" / f"{safe}.json"


def load(username: str) -> Briefing | None:
    p = _path(username)
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text())
        return Briefing(**raw)
    except Exception as e:
        logger.warning("zahnfee briefing lesen fehlgeschlagen: %s", e)
        return None


def save(briefing: Briefing, username: str) -> None:
    p = _path(username)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(briefing), ensure_ascii=False, indent=2))


def today_str() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
