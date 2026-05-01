"""Master-Agents bekommen Symlinks zu allen Projekt-Workspaces in denen ihr
Owner Member ist. Pfad: `<master-workspace>/projects/<sanitized-name>` →
`<projects-workspace>/<project-id>/`.

Sync-Operationen sind idempotent — einfach nach jedem Member-Change aufrufen.
Symlinks die zu nicht-existenten Pfaden zeigen werden beim nächsten Sync
aufgeräumt.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from hydrahive.agents._paths import workspace_for
from hydrahive.projects._paths import workspace_path as project_workspace
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]")


def _safe_name(project_name: str, project_id: str) -> str:
    safe = _NAME_RE.sub("_", project_name.strip()).strip("_.")
    return safe or f"project-{project_id[:8]}"


def _master_agents_for(username: str) -> list[dict]:
    from hydrahive.agents import config as agent_config
    return [a for a in agent_config.list_by_owner(username)
            if a.get("type") == "master"]


def _projects_dir_for_master(master: dict) -> Path:
    ws = workspace_for(master)
    return ws / "projects"


def _projects_for(username: str) -> list[dict]:
    from hydrahive.projects import config as project_config
    return project_config.list_for_user(username)


def sync_links_for_user(username: str) -> None:
    """Räumt + setzt alle Project-Symlinks für jeden Master-Agent des Users.
    Bei Member-Changes oder Master-Agent-Anlage aufrufen."""
    masters = _master_agents_for(username)
    if not masters:
        return
    projects = _projects_for(username)
    expected = {
        _safe_name(p["name"], p["id"]): project_workspace(p["id"])
        for p in projects
    }
    for master in masters:
        links_dir = _projects_dir_for_master(master)
        links_dir.mkdir(parents=True, exist_ok=True)
        existing = {entry.name: entry for entry in links_dir.iterdir()
                    if entry.is_symlink() or not entry.exists()}
        for name, entry in existing.items():
            if name not in expected:
                try:
                    entry.unlink()
                except OSError as e:
                    logger.warning("Symlink-Cleanup %s: %s", entry, e)
        for name, target in expected.items():
            link = links_dir / name
            if link.is_symlink():
                if Path(str(link.readlink())) == target:
                    continue
                link.unlink(missing_ok=True)
            elif link.exists():
                logger.warning("Workspace-Link %s ist kein Symlink — überspringe", link)
                continue
            try:
                link.symlink_to(target)
            except OSError as e:
                logger.warning("Symlink %s → %s: %s", link, target, e)


def sync_links_for_project(project_id: str) -> None:
    """Wird beim Project-Create/-Delete/-Update aufgerufen — sync für alle
    aktuellen + ehemaligen Members."""
    from hydrahive.projects import config as project_config
    cfg = project_config.get(project_id)
    users: set[str] = set()
    if cfg:
        users.update(cfg.get("members", []))
        if cfg.get("created_by"):
            users.add(cfg["created_by"])
    # Für robustes Cleanup auch alle Owner mit existierendem Master-Workspace
    if settings.agents_dir.exists():
        from hydrahive.agents import config as agent_config
        for a in agent_config.list_all():
            if a.get("type") == "master" and a.get("owner"):
                users.add(a["owner"])
    for user in users:
        sync_links_for_user(user)
