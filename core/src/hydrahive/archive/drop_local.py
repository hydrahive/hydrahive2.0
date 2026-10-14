"""Lokale Kopie löschen (Spec archiv-system.md, Etappe 3b).

Nur Pakete (.tar.gz mit .json), die geprüft auf dem Server liegen. Läuft als Auftrag `drop_local` in der Reihe der
Lösch-Aufträge. Je Paket unmittelbar vor dem Löschen: vom Server ganz zurücklesen, sha256 mit der lokalen .json
vergleichen, Server-.json prüfen. Erst dann .json auf „remote_only“ und die lokale Datei weg. Stimmt etwas nicht:
Paket bleibt, kommt neu in die Kopier-Reihe. Neustart mittendrin → `rollback` setzt „verified“ zurück, wo die Datei
noch da ist.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone

from hydrahive.archive import _remote_files as rf
from hydrahive.archive import location
from hydrahive.archive._paths import KINDS, archive_root

logger = logging.getLogger(__name__)

TARGET = "drop_local"                        # ein Auftrag zur Zeit (jobs.busy)
_PATH = re.compile(rf"^(?:{'|'.join(KINDS)})/[A-Za-z0-9_-]+\.tar\.gz$")
_ABORT = ("unreachable", "auth_failed")      # Server weg: ganzen Auftrag beenden statt jedes Paket abwarten


class DropError(Exception):
    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code, self.status = code, status


def _meta(rel: str) -> dict | None:
    try:
        meta = json.loads(rf.meta_path(rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return meta if isinstance(meta, dict) else None


def _droppable(rel: str) -> bool:
    meta = _meta(rel)
    return bool(meta and (meta.get("remote") or {}).get("state") == "verified" and (archive_root() / rel).is_file())


def candidates() -> list[str]:
    """Alle Pakete, deren lokale Kopie gelöscht werden darf."""
    from hydrahive.archive import catalog
    rels = [e["path"].replace("\\", "/") for e in catalog.list_entries()
            if not e["manual"] and e.get("local", True) and (e.get("remote") or {}).get("state") == "verified"]
    return [r for r in rels if _PATH.match(r)]           # ungewöhnliche Namen bleiben hier, statt alles zu kippen


def select(paths: list[str], all_verified: bool = False) -> list[str]:
    from hydrahive.archive import remote_config
    if not remote_config.is_active():
        raise DropError("archive_remote_inactive", 409)
    if all_verified:
        rels = candidates()
    else:
        if any(not isinstance(p, str) or not _PATH.match(p) for p in paths):
            raise DropError("archive_path_invalid", 400)
        rels = list(dict.fromkeys(paths))
        if any(not _droppable(r) for r in rels):
            raise DropError("archive_not_on_server", 409)
    if not rels:
        raise DropError("archive_nothing_selected", 400)
    return rels


def submit(*, paths: list[str] | None = None, all_verified: bool = False, actor: str) -> str:
    from hydrahive.archive import jobs
    rels = select(paths or [], all_verified)
    total = sum((archive_root() / r).stat().st_size for r in rels)
    name = (_meta(rels[0]) or {}).get("name") or rels[0] if len(rels) == 1 else f"{len(rels)} Pakete"
    return jobs.submit(TARGET, TARGET, "drop", actor=actor, name=name,
                       extra={"paths": rels, "bytes_total": total, "files_total": len(rels)})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _remove_local(path) -> None:
    path.unlink()


def _check(remote, rel: str, want: str, job: dict) -> None:
    """Server-Kopie ganz zurücklesen und mit der lokalen Prüfsumme vergleichen, dann die Server-.json."""
    from hydrahive.archive.remote_smb import RemoteError
    h = hashlib.sha256()
    for chunk in remote.read_chunks(rel):
        h.update(chunk)
        job["bytes_done"] += len(chunk)
    if h.hexdigest() != want:
        raise RemoteError("verify_failed")
    try:
        server = json.loads(b"".join(remote.read_chunks(rel + ".json")))
    except ValueError as e:
        raise RemoteError("verify_failed") from e
    if not isinstance(server, dict) or server.get("sha256") != want:
        raise RemoteError("verify_failed")


def _drop_one(remote, rel: str, job: dict) -> str | None:
    """Gibt den Grund zurück, wenn das Paket hier bleibt."""
    from hydrahive.archive import remote_sync
    from hydrahive.archive.remote_smb import RemoteError
    local, meta = archive_root() / rel, _meta(rel)
    if meta is None or not local.is_file():
        return "gone"
    st = meta.get("remote") or {}
    if st.get("state") != "verified":
        return "not_on_server"
    size = local.stat().st_size
    try:
        _check(remote, rel, meta.get("sha256") or "", job)
    except RemoteError as e:
        if e.code in _ABORT:
            raise
        kind, file = rel.split("/", 1)
        rf.set_remote(rel, state="pending")
        remote_sync.enqueue_packages([{"kind": kind, "file": file}])       # neu hochladen
        logger.warning("Lokale Kopie von %s bleibt: Server-Kopie %s", rel, e.code)
        return e.code
    with remote_sync._lock:                               # die Kopier-Reihe reiht in diesem Moment nichts ein
        if (rf.remote_of(rel) or {}).get("state") != "verified":
            return "not_on_server"
        rf.set_remote(rel, **{**st, "state": "remote_only", "dropped_at": _now()})
        _remove_local(local)
    job["freed_bytes"] += size
    return None


def execute(job: dict) -> dict:
    from hydrahive.archive import jobs, remote_config, remote_smb
    job.update(state="running", step="check", done_paths=job.get("done_paths") or [], kept=[],
               freed_bytes=job.get("freed_bytes") or 0)
    if location.moving():
        return _fail(job, "archive_unavailable")
    if not remote_config.is_active():
        return _fail(job, "remote_inactive")
    try:
        remote = remote_smb.connect(remote_config.load())
    except remote_smb.RemoteError as e:
        return _fail(job, e.code)
    try:
        for rel in job["paths"]:
            if rel in job["done_paths"]:
                continue
            if location.moving():                        # Umzug inzwischen gestartet: nichts mehr anfassen
                return _fail(job, "archive_unavailable")
            reason = _drop_one(remote, rel, job)
            if reason:
                job["kept"].append({"path": rel, "reason": reason})
            else:
                job["done_paths"].append(rel)
            jobs.save(job)
    except remote_smb.RemoteError as e:
        return _fail(job, e.code)
    except Exception:  # noqa: BLE001 – sonst hinge der Auftrag für immer auf „läuft“
        logger.exception("Lokale Kopie löschen: unerwarteter Fehler")
        rollback(job)
        return _fail(job, "unexpected")
    finally:
        remote.close()
    job["state"], job["step"] = "done", "done"
    jobs.save(job)
    logger.info("Lokale Kopien gelöscht: %d, behalten: %d, frei: %d Bytes", len(job["done_paths"]),
                len(job["kept"]), job["freed_bytes"])
    return job


def _fail(job: dict, code: str) -> dict:
    from hydrahive.archive import jobs
    job["state"], job["error"] = "failed", code
    jobs.save(job)
    logger.warning("Lokale Kopie löschen abgebrochen (%s), gelöscht bis dahin: %d", code, len(job["done_paths"]))
    return job


def rollback(job: dict) -> None:
    """Nach Neustart: Pakete, deren Datei noch da ist, stehen wieder auf „verified“ (nichts geht verloren)."""
    for rel in job.get("paths") or []:
        meta = _meta(rel)
        st = (meta or {}).get("remote") or {}
        if st.get("state") == "remote_only" and (archive_root() / rel).is_file():
            rf.set_remote(rel, **{**{k: v for k, v in st.items() if k != "dropped_at"}, "state": "verified"})
