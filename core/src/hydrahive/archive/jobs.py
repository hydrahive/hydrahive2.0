"""Reihe der Lösch-Aufträge (Spec archiv-system.md, Etappe 2).

Immer nur ein Auftrag zur Zeit, in einem eigenen Thread (die Ereignisschleife bleibt frei).
Zustand in config_dir/archive-jobs.json. Nach einem Neustart (`recover`):
- Auftrag vor Schritt 6 → zurückrollen (Agenten wieder auf alten Status, Freigabe an, Pakete weg).
- Auftrag in Schritt 6 → zu Ende löschen (die Daten liegen geprüft im Archiv).
- Wartende Aufträge laufen weiter – sie sind bestätigt und haben noch nichts angefasst.
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import threading
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

STATE_NAME = "archive-jobs.json"
_HIDDEN = ("plan", "lock")          # intern, nicht in der API

_lock = threading.RLock()
_thread: threading.Thread | None = None
_state: dict = {"queue": [], "running": None, "done": []}
_loop: asyncio.AbstractEventLoop | None = None


class JobConflict(Exception):
    """Für dieses Objekt läuft oder wartet schon ein Auftrag."""


def _path() -> Path:
    return Path(settings.config_dir) / STATE_NAME


def _persist() -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(_state, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    os.replace(tmp, p)


def _load() -> dict:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"queue": [], "running": None, "done": []}
    except (OSError, ValueError):
        logger.exception("Lösch-Aufträge unlesbar, beginne leer")
        return {"queue": [], "running": None, "done": []}
    return {"queue": list(data.get("queue") or []), "running": data.get("running"),
            "done": list(data.get("done") or [])}


def _public(job: dict | None) -> dict | None:
    if job is None:
        return None
    return {k: copy.deepcopy(v) for k, v in job.items() if k not in _HIDDEN}


def list_jobs() -> dict:
    with _lock:
        return {"running": _public(_state["running"]), "queued": [_public(j) for j in _state["queue"]],
                "done": [_public(j) for j in _state["done"]]}


def busy(target_id: str) -> bool:
    with _lock:
        jobs = _state["queue"] + ([_state["running"]] if _state["running"] else [])
        return any(j["target"] == target_id for j in jobs)


def submit(kind: str, target_id: str, mode: str, *, actor: str, name: str | None = None,
           extra: dict | None = None) -> str:
    from hydrahive.archive.deletion import new_job
    job = new_job(kind, target_id, mode, actor)
    job.update(extra or {}, name=name or target_id)
    with _lock:
        if busy(target_id):
            raise JobConflict(target_id)
        _state["queue"].append(job)
        _persist()
    logger.info("Löschauftrag %s eingereiht: %s %s (%s) von %s", job["id"], kind, target_id, mode, actor)
    _start_worker()
    return job["id"]


def save(job: dict) -> None:
    """Zwischenstand des laufenden Auftrags sichern (von deletion.py)."""
    with _lock:
        if _state["running"] is not None and _state["running"]["id"] == job["id"]:
            _state["running"] = job
            _persist()


def _finished(job: dict) -> None:
    with _lock:
        _state["running"] = None
        _state["done"].insert(0, job)
        del _state["done"][settings.archive_jobs_keep:]
        _persist()


def process_queue() -> None:
    """Arbeitet die Reihe ab, bis sie leer ist (Hintergrund-Thread; in Tests direkt)."""
    while True:
        with _lock:
            if _state["running"] is not None or not _state["queue"]:
                return
            job = _state["queue"].pop(0)
            _state["running"] = job
            _persist()
        _finished(_run(job))


def _run(job: dict) -> dict:
    from hydrahive.archive import _job_kinds
    return _job_kinds.run(job)


def _worker() -> None:
    try:
        process_queue()
    except Exception:  # noqa: BLE001 – Hintergrund-Thread darf nie still sterben
        logger.exception("Lösch-Reihe unerwartet abgebrochen")


def _start_worker() -> None:
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        _thread = threading.Thread(target=_worker, name="archive-delete", daemon=True)
        _thread.start()


def recover() -> None:
    """Nach dem Start: unterbrochenen Auftrag zurückrollen oder zu Ende löschen, dann die Reihe weiter."""
    from hydrahive.archive import deletion
    global _state
    with _lock:
        _state = _load()
        job = _state["running"]
    if job is not None:
        if job.get("step") == "delete":
            logger.warning("Löschauftrag %s war mitten im Löschen – wird zu Ende geführt", job["id"])
            try:
                job = deletion.finish(job)
            except Exception:  # noqa: BLE001
                logger.exception("Löschauftrag %s ließ sich nicht zu Ende führen", job["id"])
                job["state"], job["error"] = "failed", "delete_incomplete"
        else:
            logger.warning("Löschauftrag %s wurde unterbrochen – zurückgerollt", job["id"])
            from hydrahive.archive import _job_kinds
            _job_kinds.rollback(job)
            job["state"], job["error"] = "failed", "interrupted"
        _finished(job)
    if _state["queue"]:
        _start_worker()


async def on_start() -> None:
    """Beim Start des Dienstes (lifespan): Umzug und Aufträge in Ordnung bringen."""
    global _loop
    from hydrahive.archive.move import recover as move_recover
    _loop = asyncio.get_running_loop()
    await asyncio.to_thread(move_recover)
    await asyncio.to_thread(recover)


def after_start() -> None:
    """Beim Start nach recover(): Ordner + Freigabe einrichten, dann Kopier-Reihe zum NAS weiter.
    Steht hier, damit lifespan.py nicht wächst."""
    from hydrahive.archive import remote_sync
    from hydrahive.archive.setup import ensure_archive
    ensure_archive()
    remote_sync.on_start()


def run_async(coro, timeout: float) -> None:
    """Coroutine auf der Haupt-Schleife ausführen (z. B. Discord trennen). Ohne Schleife: auslassen."""
    if _loop is None or _loop.is_closed():
        coro.close()
        return
    asyncio.run_coroutine_threadsafe(coro, _loop).result(timeout)


def reset_for_tests() -> None:
    global _state
    with _lock:
        _state = {"queue": [], "running": None, "done": []}
        _path().unlink(missing_ok=True)
