"""Mitgelieferte System-Skills installieren und aktualisieren.

Früher wurde nur kopiert, wenn die Datei fehlte; Verbesserungen kamen nie an
(30.09.2026: 7 von 22 live veraltet). Jetzt gilt je Skill
(docs/specs/system-skills-update.md):
  fehlt                     → kopieren
  = aktuelle Fassung        → nichts
  = frühere Auslieferung    → ersetzen (Hash aus _history.json)
  sonst (Admin-Änderung)    → stehen lassen, Warnung ins Log
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_history(src: Path) -> dict[str, list[str]]:
    try:
        data = json.loads((src / "_history.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("System-Skills: _history.json fehlt oder ist kaputt, es wird nichts aktualisiert")
        return {}
    return data if isinstance(data, dict) else {}


def _atomic_copy(src: Path, dst: Path) -> None:
    fd, tmp = tempfile.mkstemp(dir=dst.parent, prefix=f".{dst.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(src.read_bytes())
        os.replace(tmp, dst)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def sync_defaults(src: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        return
    history = _load_history(src)
    for shipped in sorted(src.glob("*.md")):
        live = target / shipped.name
        if not live.exists():
            _atomic_copy(shipped, live)
            logger.info("System-Skill installiert: %s", shipped.name)
            continue
        live_sha = _sha(live)
        if live_sha == _sha(shipped):
            continue
        if live_sha in history.get(shipped.name, []):
            _atomic_copy(shipped, live)
            logger.info("System-Skill aktualisiert: %s (war eine frühere Auslieferung)", shipped.name)
        else:
            logger.warning("System-Skill %s weicht ab (Admin-Änderung?), nicht aktualisiert", shipped.name)
