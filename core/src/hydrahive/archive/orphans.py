"""Waisen finden und zum Aufräumen einreihen (Spec archiv-system.md, Etappe 2b).

Waise = Arbeitsordner `workspaces/{specialists,master}/<id>` ohne Agent, oder ein Agent, dessen
Projekt es nicht mehr gibt. „Leer“ = keine Dateien oder nur die unveränderte startup.md, die
HydraHive selbst anlegt. Das Aufräumen selbst steht in _orphan_run.py.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from hydrahive.agents._paths import is_valid_agent_id
from hydrahive.settings import settings

KINDS = ("specialists", "master")


def workspace_dir(kind: str, oid: str) -> Path:
    if kind not in KINDS or not is_valid_agent_id(oid):
        raise ValueError(f"Keine Waise: {kind}/{oid!r}")
    return settings.workspaces_dir / kind / oid


def _startup_template() -> bytes | None:
    from hydrahive.agents.bootstrap import _STARTUP_TEMPLATE
    try:
        return _STARTUP_TEMPLATE.read_bytes()
    except OSError:
        return None


def _agent_ids() -> set[str]:
    from hydrahive.agents._config_utils import list_all
    return {a["id"] for a in list_all()}


def inspect(path: Path, template: bytes | None, deadline: float) -> dict:
    """Größe, Dateizahl, ob leer. Geht nie in Laufwerke oder Symlinks hinein."""
    size, files, only_startup, complete = 0, 0, True, True
    for dirpath, dirs, names in os.walk(path, followlinks=False):
        dirs[:] = [d for d in dirs if not os.path.ismount(os.path.join(dirpath, d))]
        for n in names:
            p = os.path.join(dirpath, n)
            files += 1
            try:
                size += os.lstat(p).st_size
            except OSError:
                continue
            if only_startup and not (dirpath == str(path) and n == "startup.md" and _same(p, template)):
                only_startup = False
        if time.monotonic() > deadline:
            complete = False
            break
    return {"size": size, "files": files, "empty": complete and (files == 0 or (files == 1 and only_startup)),
            "complete": complete}


def _same(path: str, template: bytes | None) -> bool:
    if template is None:
        return False
    try:
        return Path(path).read_bytes() == template
    except OSError:
        return False


def orphan_workspaces(budget_s: float | None = None) -> list[dict]:
    deadline = time.monotonic() + (settings.archive_preview_budget_s if budget_s is None else budget_s)
    living, template, out = _agent_ids(), _startup_template(), []
    for kind in KINDS:
        root = settings.workspaces_dir / kind
        if not root.is_dir():
            continue
        for entry in sorted(os.scandir(root), key=lambda e: e.name):
            if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                continue
            if not is_valid_agent_id(entry.name) or entry.name in living:
                continue
            out.append({"id": entry.name, "kind": kind, **inspect(Path(entry.path), template, deadline)})
    return out


def is_orphan_workspace(kind: str, oid: str) -> bool:
    d = workspace_dir(kind, oid)
    return d.is_dir() and not d.is_symlink() and oid not in _agent_ids()


def orphan_agents() -> list[dict]:
    from hydrahive.agents._config_utils import list_all
    from hydrahive.projects import config as project_config
    return [{"id": a["id"], "name": a.get("name") or a["id"], "project_id": a["project_id"], "type": a.get("type")}
            for a in list_all() if a.get("project_id") and project_config.get(a["project_id"]) is None]


def scan() -> dict:
    ws = orphan_workspaces()
    return {"workspaces": ws, "agents": orphan_agents(), "complete": all(w["complete"] for w in ws)}


def submit_cleanup(*, workspaces: list[str], agents: list[str], actor: str) -> list[str]:
    """Genau diese IDs aufräumen: alle Ordner als ein Auftrag, jeder Agent als eigener Lösch-Auftrag."""
    from hydrahive.archive import jobs
    for oid in [*workspaces, *agents]:
        if not is_valid_agent_id(oid):
            raise ValueError(oid)
    ids = []
    if workspaces:
        ids.append(jobs.submit("orphans", "orphans:" + ",".join(dict.fromkeys(workspaces)), "archive", actor=actor,
                               name=f"{len(workspaces)} Arbeitsordner"))
    for aid in agents:
        ids.append(jobs.submit("orphan_agent", aid, "archive", actor=actor))
    return ids
