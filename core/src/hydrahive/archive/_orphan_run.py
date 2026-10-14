"""Auftrag „Waisen-Ordner aufräumen“ (Spec archiv-system.md, Etappe 2b).

Ordner für Ordner: unmittelbar vorher prüfen, ob es noch eine Waise ist. Leer → entfernen.
Mit Inhalt → packen (Paketname wird vorher im Auftrag gemerkt), prüfen, dann entfernen.
Ein Neustart rollt nur das Paket des Ordners zurück, der noch nicht entfernt war (jobs.recover).
"""
from __future__ import annotations

import logging
import time

from hydrahive.archive import _pack_plan, orphans, package
from hydrahive.archive._paths import kind_dir
from hydrahive.archive.package import ArchiveBusy
from hydrahive.archive.safe_rm import remove_tree
from hydrahive.archive.verify import VerifyError, verify

logger = logging.getLogger(__name__)

REASON = "orphan"


def targets(job: dict) -> list[str]:
    return [i for i in job["target"].split(":", 1)[1].split(",") if i]


def execute(job: dict) -> dict:
    from hydrahive.archive import jobs
    job.update(state="running", step="pack", done_ids=job.get("done_ids") or [], skipped=[])
    template = orphans._startup_template()
    for oid in targets(job):
        if oid in job["done_ids"]:
            continue
        kind = next((k for k in orphans.KINDS if orphans.is_orphan_workspace(k, oid)), None)
        if kind is None:                                    # inzwischen wieder zugeordnet oder schon weg
            job["skipped"].append(oid)
            continue
        path = orphans.workspace_dir(kind, oid)
        info = orphans.inspect(path, template, time.monotonic() + 3600)
        job["bytes_total"] += info["size"]
        if not info["empty"]:
            code = _pack(job, kind, oid, path, jobs.save)
            if code:
                job["state"], job["error"] = "failed", code
                jobs.save(job)
                return job
        job["leftovers"] += remove_tree(path)
        job["done_ids"].append(oid)
        job.setdefault("made", []).extend(p for p in job["packages"] if p.get("source") == oid)
        job["packages"] = [p for p in job["packages"] if p.get("source") != oid]    # fertig: nicht mehr zurückrollen
        jobs.save(job)
    job["state"], job["step"] = "done", "done"
    jobs.save(job)
    from hydrahive.archive import remote_sync
    remote_sync.enqueue_packages(job.get("made") or [])           # Kopie aufs NAS, falls aktiv (Etappe 3)
    logger.info("Waisen-Auftrag %s fertig: %d entfernt, %d übersprungen", job["id"], len(job["done_ids"]),
                len(job["skipped"]))
    return job


def _pack(job: dict, kind: str, oid: str, path, save) -> str | None:
    def started(target) -> None:
        job["packages"].append({"kind": target.parent.name, "file": target.name, "source": oid})
        save(job)

    def progress(size: int) -> None:
        job["bytes_done"] += size

    try:
        meta = package.pack(kind="agents", name=f"Arbeitsordner {oid[:8]}", source_id=oid, owner=None,
                            reason=REASON, sources=[("workspace", path)], extra={"workspace_kind": kind},
                            on_file=progress, on_target=started)
        verify(kind_dir("agents") / meta["file"])
    except VerifyError:
        rollback(job)
        return "verify_failed"
    except ArchiveBusy:
        rollback(job)
        return "archive_unavailable"
    except OSError:
        logger.exception("Waisen-Auftrag %s: Packen von %s gescheitert", job["id"], oid)
        rollback(job)
        return "pack_failed"
    job["package"] = meta["file"]
    return None


def rollback(job: dict) -> None:
    """Nur Pakete von Ordnern, die noch nicht entfernt sind (die fertigen bleiben im Archiv)."""
    _pack_plan.discard([{"kind": p["kind"], "file": p["file"]} for p in job.get("packages") or []])
    job["packages"] = []
