"""Löschen mit Archiv: sperren → messen → Platz → packen → prüfen → löschen (Spec archiv-system.md, Etappe 2).

`run()` arbeitet einen Auftrag ab und gibt sein Ergebnis zurück. Es wirft nie für erwartbare
Fehler (die stehen in `error`). Den Zustand schreibt `_save` laufend in jobs.py – so weiß ein
Neustart, ob zurückgerollt (vor Schritt 6) oder zu Ende gelöscht (ab Schritt 6) werden muss.
"""
from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from hydrahive.archive import _bundle, _lock, _pack_plan, _plan, _remove, location
from hydrahive.archive._paths import archive_root
from hydrahive.archive.package import ArchiveBusy
from hydrahive.archive.verify import VerifyError
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

MODES = ("archive", "permanent")


def free_bytes(path: Path) -> int:
    probe = Path(path)
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return shutil.disk_usage(probe).free


def _save(job: dict) -> None:
    from hydrahive.archive import jobs
    jobs.save(job)


def new_job(kind: str, target_id: str, mode: str, actor: str) -> dict:
    return {"id": uuid.uuid4().hex[:12], "kind": kind, "target": target_id, "mode": mode, "actor": actor,
            "state": "queued", "step": "queued", "error": None, "name": target_id, "packages": [],
            "bytes_total": 0, "files_total": 0, "bytes_done": 0, "leftovers": [], "lock": None, "plan": None}


def run(kind: str, target_id: str, mode: str, *, actor: str) -> dict:
    """Ohne Reihe direkt ausführen (Tests, Waisen). Die API geht über jobs.submit()."""
    return execute(new_job(kind, target_id, mode, actor))


def preview(kind: str, target_id: str) -> dict:
    from hydrahive.archive.preview import preview as _preview
    return _preview(kind, target_id)


def execute(job: dict) -> dict:
    """Schritte 1–6 für einen Auftrag. Rückgabe = der Auftrag mit state done|failed."""
    job["state"] = "running"
    try:
        _guard(job)
        job["plan"] = _plan.build(job["kind"], job["target"])
        job["name"] = job["plan"]["name"]
    except _plan.PlanError as e:
        return _fail(job, e.code)
    plan = job["plan"]
    job["step"] = "lock"
    job["lock"] = _lock.lock(_agents(plan), _plan.all_session_ids(plan), [p["id"] for p in plan["projects"]])
    _save(job)
    try:
        if job["mode"] == "archive":
            code = _archive(job)
            if code:
                return _rollback(job, code)
        stuck = _unmount(plan)
        if stuck:
            job["leftovers"] = stuck
            return _rollback(job, "umount_failed")
    except Exception:
        logger.exception("Löschauftrag %s: unerwarteter Fehler vor dem Löschen", job["id"])
        return _rollback(job, "unexpected")
    return finish(job)


def _guard(job: dict) -> None:
    if job["mode"] not in MODES:
        raise _plan.PlanError("invalid_mode")
    if job["kind"] == "user":
        from hydrahive.api.middleware import users
        u = users.get_by_username(job["target"])
        if u and u["role"] == "admin" and sum(1 for x in users.list_users() if x["role"] == "admin") <= 1:
            raise _plan.PlanError("last_admin_cannot_delete")
    if job["mode"] == "archive" and location.moving():
        raise _plan.PlanError("archive_unavailable")


def _archive(job: dict) -> str | None:
    """Schritte 2–5. Gibt einen Fehlercode zurück oder None."""
    work = _bundle.work_dir(job["id"])
    try:
        job["step"] = "measure"
        items = _pack_plan.bundles(job["plan"], work)
        sizes = [_pack_plan.measure(i["sources"]) for i in items]
        job["bytes_total"], job["files_total"] = sum(s[0] for s in sizes), sum(s[1] for s in sizes)
        need = int(job["bytes_total"] * (1 + settings.archive_space_reserve))
        if free_bytes(archive_root()) < need:
            return "not_enough_space"
        job["step"] = "pack"
        _save(job)

        def progress(size: int) -> None:
            job["bytes_done"] += size

        def started(path: Path) -> None:               # vor dem Schreiben merken: Neustart findet es
            job["packages"].append({"kind": path.parent.name, "file": path.name})
            _save(job)

        try:
            metas = _pack_plan.pack_all(items, progress, started)
        except VerifyError:
            return "verify_failed"
        except ArchiveBusy:
            return "archive_unavailable"
        except OSError:
            logger.exception("Löschauftrag %s: Packen gescheitert", job["id"])
            return "pack_failed"
        job["packages"] = [{"kind": m["kind"], "file": m["file"]} for m in metas]
        job["package"] = metas[-1]["file"]
        return None
    finally:
        _bundle.drop_work_dir(job["id"])


def _unmount(plan: dict) -> list[str]:
    from hydrahive.projects._delete import unmount_all
    stuck: list[str] = []
    for p in plan["projects"]:
        stuck += unmount_all(p["id"])
    return stuck


def finish(job: dict) -> dict:
    """Schritt 6. Wiederholbar: nach einem Neustart einfach noch einmal aufrufen."""
    from hydrahive.projects._delete import remove_rest
    plan = job["plan"]
    job["step"] = "delete"
    _save(job)
    _remove.sessions(_plan.all_session_ids(plan))
    for p in plan["projects"]:
        _remove.unhook_sessions(p["unhook"])
        for a in p["agents"]:
            _remove.agent(a["id"])
        job["leftovers"] += remove_rest(p["id"], {"members": p["members"], "created_by": p["owner"]})
    for a in plan["agents"]:
        _remove.agent(a["id"])
    if plan.get("user"):
        _finish_user(plan["user"], job["actor"])
    job["leftovers"] = sorted(set(job["leftovers"]))
    job["state"], job["step"] = "done", "done"
    _save(job)
    logger.info("Löschauftrag %s fertig: %s %s (%s)", job["id"], job["kind"], job["target"], job["mode"])
    return job


def _finish_user(user: dict, actor: str) -> None:
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    name = user["name"]
    _remove.hand_over_agents([a for a in (agent_config.get(i) for i in user.get("hand_over", [])) if a])
    _remove.memberships(name, [p for p in (project_config.get(i) for i in user.get("memberships", [])) if p])
    _remove.user_data(name, user["user_id"])
    from hydrahive.api.middleware import users
    actor_user = users.get_by_username(actor)
    _remove.account(name, user["user_id"], actor_user["user_id"] if actor_user else actor)


def _agents(plan: dict) -> list[dict]:
    from hydrahive.agents import config as agent_config
    return [a for a in (agent_config.get(i) for i in _plan.all_agent_ids(plan)) if a]


def _rollback(job: dict, code: str) -> dict:
    rollback_lock(job)
    return _fail(job, code)


def rollback_lock(job: dict) -> None:
    if job.get("lock"):
        names = {p["id"]: p["name"] for p in (job.get("plan") or {}).get("projects", [])}
        _lock.release(job["lock"], names)
    _pack_plan.discard([{"kind": p["kind"], "file": p["file"]} for p in job.get("packages") or []])
    job["packages"] = []
    _bundle.drop_work_dir(job["id"])


def _fail(job: dict, code: str) -> dict:
    job["state"], job["error"] = "failed", code
    _save(job)
    logger.warning("Löschauftrag %s abgebrochen (%s): %s %s – nichts gelöscht", job["id"], code, job["kind"],
                   job["target"])
    return job
