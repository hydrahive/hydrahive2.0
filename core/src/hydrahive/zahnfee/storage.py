"""Zahnfee-Briefing — lesen/schreiben aus HH_DATA_DIR/zahnfee_briefing.json."""
from __future__ import annotations

import json
import logging
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


def _path() -> Path:
    return settings.data_dir / "zahnfee_briefing.json"


def load() -> Briefing | None:
    p = _path()
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text())
        return Briefing(**raw)
    except Exception as e:
        logger.warning("zahnfee briefing lesen fehlgeschlagen: %s", e)
        return None


def save(briefing: Briefing) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(briefing), ensure_ascii=False, indent=2))


def today_str() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
