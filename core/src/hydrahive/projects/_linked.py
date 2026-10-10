"""Verknüpfte Projekte: Projekt-Agent und Spezialisten eines Projekts lesen weitere Projekte (docs/specs/linked-projects.md).

Projekt-Feld ``linked_projects`` (Liste von Projekt-IDs). Wirksam in einem Lauf nur für Agenten des Projekts (Projekt-
Agent, Spezialisten mit ``project_id``) und nur für verknüpfte Projekte, in denen der NUTZER DES LAUFS mindestens
``read`` hat – sonst wäre der Agent eine Hintertür in fremde Projekte. Nur lesen: Schreiben bleibt im eigenen Projekt.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from hydrahive.projects import _members_model
from hydrahive.projects._paths import workspace_path
from hydrahive.tools._path import PathOutsideWorkspace, safe_path

logger = logging.getLogger(__name__)
MAX_LINKS = 20
LINK_DIR = "linked"
_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]")


class LinkError(ValueError):
    def __init__(self, code: str, project: str = ""):
        super().__init__(code)
        self.code, self.project = code, project


def _role_ok(project: dict | None, username: str, role: str, need: str) -> bool:
    if project is None:
        return False
    return role == "admin" or _members_model.has_at_least(_members_model.role_of(project, username), need)


def _link_name(project: dict) -> str:
    return _NAME_RE.sub("_", project["name"].strip()).strip("_.") or f"project-{project['id'][:8]}"


def set_links(project_id: str, links: object, *, username: str, role: str) -> list[str]:
    """Liste setzen. Wer: Admin im eigenen Projekt UND ≥ write in jedem verknüpften (System-Admin immer)."""
    from hydrahive.projects import config as project_config
    project = project_config.get(project_id)
    if project is None:
        raise LinkError("project_not_found")
    if not _role_ok(project, username, role, "admin"):
        raise LinkError("project_admin_required")
    if not isinstance(links, list) or len(links) > MAX_LINKS or len(set(map(str, links))) != len(links):
        raise LinkError("linked_projects_invalid")
    for pid in links:
        other = project_config.get(pid) if isinstance(pid, str) and pid != project_id else None
        if other is None:
            raise LinkError("linked_projects_invalid", str(pid))
        if not _role_ok(other, username, role, "write"):
            raise LinkError("linked_project_no_access", pid)
    project_config.update(project_id, linked_projects=list(links))
    sync_link_dir(project_id)
    return list(links)


def belongs_to(agent: dict | None, project: dict) -> bool:
    if not agent:
        return False
    return agent.get("id") == project.get("agent_id") or (
        agent.get("type") == "specialist" and agent.get("project_id") == project.get("id"))


def effective(agent: dict | None, project_id: str | None, username: str) -> list[str]:
    """Verknüpfte Projekte, die DIESER Lauf lesen darf (Agent gehört zum Projekt, Nutzer ist dort Mitglied)."""
    from hydrahive.api.middleware import users
    from hydrahive.projects import config as project_config
    project = project_config.get(project_id) if project_id else None
    if project is None or not belongs_to(agent, project):
        return []
    user = users.get_by_username(username) or {}
    role = user.get("role", "user")
    return [pid for pid in project.get("linked_projects") or []
            if _role_ok(project_config.get(pid), username, role, "read")]


def read_path(ctx, requested: str) -> Path:
    """Wie safe_path, erlaubt aber zusätzlich Ziele in wirksam verknüpften Projekten – NUR für lesende Werkzeuge."""
    try:
        return safe_path(ctx.workspace, requested)
    except PathOutsideWorkspace:
        pass
    from hydrahive.agents import config as agent_config
    p = Path(requested)
    real = (p if p.is_absolute() else ctx.workspace / p).resolve()
    for pid in effective(agent_config.get(ctx.agent_id), ctx.project_id, ctx.user_id):
        root = workspace_path(pid).resolve()
        if real == root or root in real.parents:
            return real
    raise PathOutsideWorkspace(f"Pfad außerhalb Workspace: {requested}")


def sync_link_dir(project_id: str) -> None:
    """Ordner ``linked/<Name>`` im eigenen Workspace: Symlinks auf die verknüpften Projekte (wie beim Master)."""
    from hydrahive.projects import config as project_config
    project = project_config.get(project_id)
    if project is None:
        return
    d = workspace_path(project_id) / LINK_DIR
    wanted = {}
    for pid in project.get("linked_projects") or []:
        other = project_config.get(pid)
        if other:
            wanted[_link_name(other)] = workspace_path(pid)
    if not wanted and not d.exists():
        return
    d.mkdir(parents=True, exist_ok=True)
    for entry in d.iterdir():
        if entry.is_symlink() and (entry.name not in wanted or Path(str(entry.readlink())) != wanted[entry.name]):
            entry.unlink()
    for name, target in wanted.items():
        link = d / name
        if not link.is_symlink() and not link.exists():
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError as e:
                logger.warning("Verknüpfung %s → %s: %s", link, target, e)


def hint(agent: dict | None, project: dict, username: str) -> str:
    """Zeilen für den System-Prompt – nur wirksame Verknüpfungen."""
    from hydrahive.projects import config as project_config
    pids = effective(agent, project.get("id"), username)
    if not pids:
        return ""
    lines = ["Verknüpfte Projekte (nur lesen): file_read und die Such-Werkzeuge dürfen dort lesen; schreiben nur im "
             "eigenen Projekt – Änderungen dort per Task an den dortigen Agenten."]
    for pid in pids:
        other = project_config.get(pid)
        if other:
            lines.append(f"  - {other['name']}: ./{LINK_DIR}/{_link_name(other)}/ ({workspace_path(pid)})")
    return "\n".join(lines)


def sync_pointing_to(project_id: str) -> None:
    """Nach Umbenennen/Löschen eines Projekts: ``linked/``-Ordner aller Projekte nachziehen, die es verknüpfen."""
    from hydrahive.projects import config as project_config
    for p in project_config.list_all():
        if project_id in (p.get("linked_projects") or []) and p["id"] != project_id:
            sync_link_dir(p["id"])
