"""Kopier-Reihe zum externen Server (Spec archiv-system.md, Etappe 3).

Eigener Thread, unabhängig von der Lösch-Reihe: Ein langsames oder fehlendes NAS hält kein Löschen
auf. Hochladen → vom Server zurücklesen → sha256 vergleichen → erst dann „verified“. Fehlschlag:
Eintrag bleibt, neuer Versuch nach 1 min, 5 min, 30 min, dann stündlich – ohne Rückfrage.
Zustand in config_dir/archive-remote-queue.json, Stand je Paket in seiner .json (`remote`).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from hydrahive.archive import _remote_files as rf
from hydrahive.archive import remote_config
from hydrahive.archive._paths import archive_root
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

NAME = "archive-remote-queue.json"
BACKOFF_S = (60, 300, 1800, 3600)

_lock = threading.RLock()
_state: dict | None = None


def _now() -> float:
    return time.time()


def _path() -> Path:
    return Path(settings.config_dir) / NAME


def _load() -> dict:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
        return {"items": list(data.get("items") or []), "last_error": data.get("last_error")}
    except (OSError, ValueError):
        return {"items": [], "last_error": None}


def _st() -> dict:
    global _state
    if _state is None:
        _state = _load()
    return _state


def _persist() -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(_st(), ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def _queue(rel: str) -> bool:
    """Unter derselben Sperre wie „lokale Kopie löschen“ (3b): Was hier nicht mehr liegt, kommt nicht in die Reihe."""
    with _lock:
        if any(i["rel"] == rel for i in _st()["items"]) or not (archive_root() / rel).is_file():
            return False
        _st()["items"].append({"rel": rel, "tries": 0, "next_at": 0})
        _persist()
        rf.set_remote(rel, state="pending")
    return True


def enqueue_packages(packages: list[dict]) -> None:
    """Nach einem fertigen Auftrag (Löschen, Waisen): die neuen Pakete kopieren, falls ein Server aktiv ist."""
    if not packages or not remote_config.is_active():
        return
    for p in packages:
        _queue(f"{p['kind']}/{p['file']}")
    _start_worker()


def sync() -> int:
    """Abgleich: Was auf dem Server fehlt oder anders ist, kommt in die Reihe. Gibt die Zahl zurück."""
    from hydrahive.archive import remote_smb
    if not remote_config.is_active():
        return 0
    remote = remote_smb.connect(remote_config.load())
    queued = 0
    for rel in rf.files():
        try:
            size = (archive_root() / rel).stat().st_size
        except OSError:                                    # inzwischen weg (z. B. lokale Kopie gelöscht)
            continue
        if rf.remote_of(rel).get("state") == "verified" and remote.size(rel) == size:
            continue
        queued += _queue(rel)
    _start_worker()
    return queued


def _copy(remote, rel: str) -> None:
    from hydrahive.archive.remote_smb import RemoteError
    local = archive_root() / rel
    want = rf.sha_local(rel)
    remote.put(rel, local)
    h = hashlib.sha256()
    for chunk in remote.read_chunks(rel):
        h.update(chunk)
    if h.hexdigest() != want:
        raise RemoteError("verify_failed")
    if rf.meta_path(rel).exists():
        remote.put(rel + ".json", rf.meta_path(rel))
    rf.set_remote(rel, state="verified", sha256=want,
                verified_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))


def process_queue() -> None:
    """Alle fälligen Einträge einmal versuchen (Thread; in Tests direkt)."""
    from hydrahive.archive import remote_smb
    if not remote_config.is_active():
        return
    with _lock:
        due = [dict(i) for i in _st()["items"] if i["next_at"] <= _now()]
    if not due:
        return
    try:
        remote = remote_smb.connect(remote_config.load())
    except remote_smb.RemoteError as e:
        return _failed([i["rel"] for i in due], e.code)
    for item in due:
        rel = item["rel"]
        if not (archive_root() / rel).exists():          # z. B. verworfen oder von Hand gelöscht
            _done(rel)
            continue
        try:
            _copy(remote, rel)
        except remote_smb.RemoteError as e:
            _failed([rel], e.code)
            continue
        _done(rel)


def _done(rel: str) -> None:
    with _lock:
        _st()["items"] = [i for i in _st()["items"] if i["rel"] != rel]
        _st()["last_error"] = None
        _persist()


def _failed(rels: list[str], code: str) -> None:
    logger.info("Kopie aufs NAS verschoben (%s): %d Paket(e)", code, len(rels))
    with _lock:
        for i in _st()["items"]:
            if i["rel"] in rels:
                i["tries"] += 1
                i["next_at"] = _now() + BACKOFF_S[min(i["tries"], len(BACKOFF_S)) - 1]
        _st()["last_error"] = code
        _persist()


def summary() -> dict:
    with _lock:
        items = list(_st()["items"])
        last = _st()["last_error"]
    nxt = min((i["next_at"] for i in items), default=None)
    return {"waiting": len(items), "last_error": last,
            "next_try_in_s": max(0, round(nxt - _now())) if nxt is not None else None}


def _start_worker() -> None:
    from hydrahive.archive import _remote_worker
    _remote_worker.start()


def on_start() -> None:
    from hydrahive.archive import _remote_worker
    _remote_worker.on_start()


def reset_for_tests() -> None:
    global _state
    with _lock:
        _state = {"items": [], "last_error": None}
        _path().unlink(missing_ok=True)


def reload_for_tests() -> None:
    global _state
    with _lock:
        _state = None
