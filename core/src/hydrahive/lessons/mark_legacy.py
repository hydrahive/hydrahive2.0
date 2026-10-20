"""Bestand markieren (Spec 7): automatische `lesson.<12 hex>`-Einträge in memory.json bekommen `legacy_lesson: true`.

Nichts wird gelöscht; von Hand geschriebene Lehren (sprechende Schlüssel) bleiben unberührt. Umkehrbar mit --undo.
Aufruf: python -m hydrahive.lessons.mark_legacy [--undo]
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

AUTO_KEY = re.compile(r"^lesson\.[0-9a-f]{12}$")


def _write(path: Path, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".memory.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def run(agents_dir: Path, *, undo: bool = False) -> dict:
    files = marked = 0
    for path in sorted(Path(agents_dir).glob("*/memory.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("mark_legacy: %s übersprungen: %s", path, e)
            continue
        files += 1
        changed = 0
        for key, entry in data.items():
            if not (AUTO_KEY.match(key) and isinstance(entry, dict)):
                continue
            if undo and entry.pop("legacy_lesson", None):
                changed += 1
            elif not undo and not entry.get("legacy_lesson"):
                entry["legacy_lesson"] = True
                changed += 1
        if changed:
            _write(path, data)
        marked += changed
    return {"files": files, "marked": marked}


if __name__ == "__main__":  # pragma: no cover
    from hydrahive.settings import settings
    logging.basicConfig(level=logging.INFO)
    logger.info("mark_legacy: %s", run(settings.agents_dir, undo="--undo" in sys.argv))
