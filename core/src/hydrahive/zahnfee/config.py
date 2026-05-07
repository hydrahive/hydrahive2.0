"""Zahnfee-Konfiguration — lesen/schreiben aus HH_CONFIG_DIR/zahnfee.json."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_SOUL = """Du bist die Zahnfee — HydraHives stille Nacht-Analytikerin.

Du hast Zugriff auf die Aktivitäten der letzten Stunden und erstellst daraus
ein kompaktes Morgen-Briefing für Till. Kein Roman — kurze, klare Punkte.

Antworte IMMER in diesem exakten JSON-Format:
{
  "open": "Aufzählung offener Ideen, geplanter aber nie umgesetzter Dinge. Maximal 5 Punkte.",
  "went_well": "Was gestern gut lief, was fertig wurde, was funktioniert hat. Maximal 5 Punkte.",
  "went_badly": "Wo Zeit verloren ging, was nicht funktionierte, was frustrierend war. Maximal 5 Punkte.",
  "today": "Was heute relevant ist basierend auf gestern — konkrete Ansatzpunkte, keine Phrasen. Maximal 5 Punkte."
}

Regeln:
- Sei direkt und ehrlich, kein Schönreden
- Nur was wirklich in den Daten steht — keine Erfindungen
- Wenn eine Kategorie leer ist: leerer String ""
- Kein Markdown, kein HTML — nur Text in den Feldern
- Auf Deutsch
"""


@dataclass
class ZahnfeeConfig:
    enabled: bool = True
    model: str = ""
    run_hour: int = 3
    lookback_hours: int = 24
    source_datamining: bool = True
    source_mail: bool = False
    soul: str = DEFAULT_SOUL


def _config_path() -> Path:
    return settings.config_dir / "zahnfee.json"


def load() -> ZahnfeeConfig:
    p = _config_path()
    if not p.exists():
        return ZahnfeeConfig()
    try:
        raw = json.loads(p.read_text())
        cfg = ZahnfeeConfig()
        for f_name in asdict(cfg):
            if f_name in raw:
                setattr(cfg, f_name, raw[f_name])
        return cfg
    except Exception as e:
        logger.warning("zahnfee config lesen fehlgeschlagen: %s", e)
        return ZahnfeeConfig()


def save(cfg: ZahnfeeConfig) -> None:
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2))
