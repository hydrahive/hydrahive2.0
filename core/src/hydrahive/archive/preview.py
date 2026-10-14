"""Vorschau für den Lösch-Dialog (Spec archiv-system.md, Etappe 2, API delete-preview).

Name, was betroffen ist, was bestehen bleibt, Größe (höchstens archive_preview_budget_s gezählt,
sonst „mindestens X“), Ziel und ob „Ins Archiv“ geht.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from hydrahive.archive import _plan, location
from hydrahive.archive._paths import archive_root
from hydrahive.settings import settings


def _paths(plan: dict) -> list[Path]:
    out: list[Path] = []
    for p in plan["projects"]:
        out += [Path(p["project_dir"]), Path(p["workspace"])]
        out += [Path(a["agent_dir"]) for a in p["agents"]]
        out += [Path(a["workspace"]) for a in p["agents"] if a.get("workspace")]
    out += [Path(a["agent_dir"]) for a in plan["agents"]]
    out += [Path(a["workspace"]) for a in plan["agents"] if a.get("workspace")]
    return out


def _size(paths: list[Path], budget_s: float) -> tuple[int, bool]:
    """(Bytes, vollständig?) – bricht nach `budget_s` ab. Geht nie in eingehängte Laufwerke."""
    deadline = time.monotonic() + budget_s
    total = 0
    for root in paths:
        for dirpath, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if not os.path.ismount(os.path.join(dirpath, d))]
            for f in files:
                try:
                    total += os.lstat(os.path.join(dirpath, f)).st_size
                except OSError:
                    continue
            if time.monotonic() > deadline:
                return total, False
    return total, True


def _stays(plan: dict) -> dict:
    """Was beim Nutzer bleibt (Entscheidung 3): VMs, Container, SMB-Verbindungen. Module zählen nicht mit."""
    if plan["kind"] != "user":
        return {}
    from hydrahive.containers import db as containers_db
    from hydrahive.smbmounts import db as mounts_db
    from hydrahive.vms import db as vms_db
    name = plan["name"]
    return {"vms": len(vms_db.list_vms(owner=name)), "containers": len(containers_db.list_(owner=name)),
            "smb_mounts": len(mounts_db.list_mounts(owner=name))}


def _archive_target(size: int) -> dict:
    from hydrahive.archive.deletion import free_bytes
    from hydrahive.archive.share import SHARE_NAME, archive_share_enabled
    root = archive_root()
    target = {"path": str(root), "share": SHARE_NAME if archive_share_enabled() else None,
              "free_bytes": free_bytes(root), "possible": True, "reason": None}
    if location.moving():
        target.update(possible=False, reason="moving")
    elif target["free_bytes"] < int(size * (1 + settings.archive_space_reserve)):
        target.update(possible=False, reason="not_enough_space")
    return target


def preview(kind: str, target_id: str) -> dict:
    """PlanError("not_found") wenn es das Objekt nicht gibt."""
    plan = _plan.build(kind, target_id)
    size, complete = _size(_paths(plan), settings.archive_preview_budget_s)
    agents = [{"id": a["id"], "name": a["name"]} for a in plan["agents"]]
    for p in plan["projects"]:
        agents += [{"id": a["id"], "name": a["name"]} for a in p["agents"]]
    user = plan.get("user") or {}
    return {
        "kind": kind, "id": target_id, "name": plan["name"],
        "agents": agents, "chats": len(_plan.all_session_ids(plan)),
        "projects": [{"id": p["id"], "name": p["name"]} for p in plan["projects"]],
        "members": {p["id"]: p["members"] for p in plan["projects"]},
        "mounts_skipped": [m for p in plan["projects"] for m in p["mounts"]],
        "hand_over": len(user.get("hand_over") or []), "memberships": len(user.get("memberships") or []),
        "stays": _stays(plan),
        "size": {"bytes": size, "complete": complete},
        "archive": _archive_target(size),
    }
