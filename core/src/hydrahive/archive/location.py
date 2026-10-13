"""Wo das System-Archiv liegt und ob die Samba-Freigabe gewünscht ist.

Kein install.conf, keine Env-Variable (Till, 13.10.: alles über die Admin-Konsole, viele unbekannte
Installationen). Standard ist workspaces/archive – dieselbe Platte wie die Projektdaten. Ein anderer
Ort und der Freigabe-Schalter stehen in config_dir/archive.json und werden nur über die Admin-API
geschrieben. Eine kaputte oder unsichere Datei fällt auf den Standard zurück.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

CONFIG_NAME = "archive.json"
MOVE_STATE_NAME = "archive-move.json"   # solange sie liegt, läuft ein Umzug (archive/move.py)


def _config_path() -> Path:
    return Path(settings.config_dir) / CONFIG_NAME


def _read() -> dict:
    p = _config_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        logger.warning("Archiv-Einstellung %s unlesbar, nehme Standard: %s", p, e)
        return {}
    if not isinstance(data, dict):
        logger.warning("Archiv-Einstellung %s ist kein Objekt, nehme Standard", p)
        return {}
    return data


def _write(data: dict) -> None:
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def default_root() -> Path:
    return Path(settings.workspaces_dir) / "archive"


def archive_root() -> Path:
    raw = _read().get("local_dir")
    if isinstance(raw, str) and raw.strip() and os.path.isabs(raw.strip()):
        return Path(raw.strip())
    if raw is not None:
        logger.warning("Archiv-Ort %r ungültig (kein absoluter Pfad), nehme Standard", raw)
    return default_root()


def is_default() -> bool:
    return archive_root() == default_root()


def moving() -> bool:
    return (Path(settings.config_dir) / MOVE_STATE_NAME).exists()


def share_wanted() -> bool:
    """Während eines Umzugs immer aus – niemand soll in einen Ort schreiben, der gerade wegkopiert wird."""
    if moving():
        return False
    return share_switch()


def share_switch() -> bool:
    """Stellung des Schalters in der Admin-Konsole (Standard: an)."""
    value = _read().get("share", True)
    return value if isinstance(value, bool) else True


def set_local_dir(path: Path) -> None:
    data = _read()
    if Path(path) == default_root():
        data.pop("local_dir", None)
    else:
        data["local_dir"] = str(path)
    _write(data)


def set_share_wanted(enabled: bool) -> None:
    data = _read()
    data["share"] = bool(enabled)
    _write(data)
