"""Archiv umziehen (Spec archiv-system.md, Etappe 1b): kopieren → prüfen → umstellen → alten Ort aufräumen.

Nie Daten verlieren:
- Gelöscht wird am alten Ort nur, was vorher kopiert UND geprüft wurde (Pakete per sha256 aus der .json, sonst Größe).
- Fehler vor dem Umstellen: Kopie am Ziel weg, alter Ort bleibt aktiv.
- Zustand in config_dir/archive-move.json; recover() beim Start rollt zurück bzw. räumt fertig auf.
Fortschritt und Hintergrund-Lauf: archive/move_job.py.
"""
from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from pathlib import Path

from hydrahive.archive import location, setup
from hydrahive.archive._move_files import _cleanup, _copy_file, _files, _free_bytes, _inside, _rollback, _verify
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
RESERVE = 1.05
STATE_NAME = location.MOVE_STATE_NAME
Progress = Callable[[dict], None]


def _state_path() -> Path:
    return Path(settings.config_dir) / STATE_NAME


def read_state() -> dict | None:
    try:
        data = json.loads(_state_path().read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _write_state(data: dict) -> None:
    tmp = _state_path().with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    os.replace(tmp, _state_path())


def check_target(target: Path) -> list[str]:
    target, current = Path(target), location.archive_root()
    problems = []
    if read_state():
        problems.append("move_running")
    if target.resolve() == current.resolve():
        return problems + ["same_location"]
    if _inside(target, current):
        problems.append("target_inside_current")
    if _inside(current, target):
        problems.append("current_inside_target")
    if target.exists() and _files(target):
        problems.append("target_not_empty")
    if not os.access(next(p for p in (target, *target.parents) if p.exists()), os.W_OK | os.X_OK):
        problems.append("target_not_writable")
    needed = sum((current / f).lstat().st_size for f in _files(current)) if current.is_dir() else 0
    if _free_bytes(target) < needed * RESERVE:
        problems.append("not_enough_space")
    return problems


def run_move(target: Path, on_progress: Progress | None = None) -> dict:
    """Zieht das Archiv nach `target` um. Blockiert; für den Hintergrund siehe move_job.start()."""
    target, source = Path(target), location.archive_root()
    files = _files(source)
    total = sum((source / f).lstat().st_size for f in files)
    st = {"state": "copying", "source": str(source), "target": str(target), "copied": [],
          "total_bytes": total, "copied_bytes": 0, "total_files": len(files),
          # check_target verlangt ein leeres Ziel → nach Abbruch gehört dort alles dem Umzug (recover).
          "target_was_empty": not (target.exists() and _files(target))}
    report = on_progress or (lambda s: None)
    _write_state(st)
    setup.ensure_archive()          # Freigabe aus, solange umgezogen wird (location.share_wanted)
    try:
        report({k: v for k, v in st.items() if k != "copied"})
        for rel in files:
            _copy_file(source / rel, target / rel)
            st["copied"].append(rel)
            st["copied_bytes"] += (source / rel).lstat().st_size
            if len(st["copied"]) % 50 == 0:
                _write_state(st)
            report({k: v for k, v in st.items() if k != "copied"})
        st["state"] = "verifying"
        _write_state(st)
        report({k: v for k, v in st.items() if k != "copied"})
        if not _verify(source, target, files):
            raise _Failed("verify_failed", "")
    except _Failed as e:
        return _abort(target, st, e.code, e.detail)
    except OSError as e:
        return _abort(target, st, "copy_failed", str(e))
    location.set_local_dir(target)
    st["state"] = "cleanup"
    _write_state(st)
    left = _cleanup(source, st["copied"])
    _state_path().unlink(missing_ok=True)
    setup.ensure_archive()
    logger.info("Archiv umgezogen: %s → %s (%d Dateien)", source, target, len(files))
    return {"state": "done", "left_behind": left, "source": str(source), "target": str(target)}


class _Failed(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(code)
        self.code, self.detail = code, detail


def _abort(target: Path, st: dict, code: str, detail: str) -> dict:
    logger.warning("Archiv-Umzug abgebrochen (%s): %s", code, detail)
    _rollback(target, st["copied"])
    _state_path().unlink(missing_ok=True)
    setup.ensure_archive()
    return {"state": "failed", "error": code, "detail": detail}


def recover() -> None:
    """Beim Start: halben Umzug zurückrollen (vor dem Umstellen) bzw. Aufräumen fortsetzen (danach)."""
    st = read_state()
    if not st:
        return
    source, target, copied = Path(st.get("source", "")), Path(st.get("target", "")), st.get("copied", [])
    if st.get("state") == "cleanup":
        left = _cleanup(source, copied)
        logger.warning("Archiv-Umzug nach Neustart fertig aufgeräumt, übrig: %d", len(left))
    else:
        # Der Zustand wird nicht nach jeder Datei geschrieben – bei leerem Ziel alles dort Liegende zurücknehmen.
        _rollback(target, _files(target) if st.get("target_was_empty") and target.is_dir() else copied)
        logger.warning("Halber Archiv-Umzug nach Neustart zurückgerollt (%s)", target)
    _state_path().unlink(missing_ok=True)
