from __future__ import annotations

import logging
import shutil
from typing import Any

from hydrahive.agents import config as agent_config
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.projects import _validation
from hydrahive.projects._config_io import (
    _normalize, _save_atomic, get, list_all, list_for_user,
)
from hydrahive.projects._paths import (
    config_path,
    ensure_workspace,
    project_dir,
)
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

__all__ = ["get", "list_all", "list_for_user", "create", "update", "delete"]


def create(
    name: str,
    *,
    description: str = "",
    members: list[str] | None = None,
    llm_model: str,
    created_by: str,
    init_git: bool = False,
    metadata: dict | None = None,
) -> dict:
    _validation.validate_name(name)
    members = members or []
    _validation.validate_members(members)

    project_id = uuid7()
    cfg: dict[str, Any] = {
        "id": project_id,
        "name": name.strip(),
        "description": description,
        "members": list(members),
        "agent_id": "",  # gleich gesetzt
        "status": "active",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "created_by": created_by,
        "git_initialized": False,
        "metadata": metadata or {},
    }
    project_dir(project_id).mkdir(parents=True, exist_ok=True)

    workspace = ensure_workspace(project_id)
    if init_git:
        from hydrahive.projects._git import init_repo
        cfg["git_initialized"] = init_repo(workspace)

    # Project-Agent automatisch anlegen
    agent = agent_config.create(
        agent_type="project",
        name=f"{name} — Projekt-Agent",
        llm_model=llm_model,
        owner=created_by,
        created_by=created_by,
        description=f"Auto-erstellt für Projekt '{name}'",
        project_id=project_id,
    )
    cfg["agent_id"] = agent["id"]
    _save_atomic(config_path(project_id), cfg)
    from hydrahive.agents._workspace_links import sync_links_for_project
    sync_links_for_project(project_id)
    logger.info("Projekt '%s' angelegt (id=%s, agent=%s)", name, project_id, agent["id"])
    return cfg



def update(project_id: str, **changes: Any) -> dict:
    cfg = get(project_id)
    if not cfg:
        raise KeyError(f"Projekt '{project_id}' nicht gefunden")
    for protected in ("id", "agent_id", "created_at", "created_by"):
        changes.pop(protected, None)
    if "name" in changes:
        _validation.validate_name(changes["name"])
    if "status" in changes:
        _validation.validate_status(changes["status"])
    if "members" in changes:
        _validation.validate_members(changes["members"])
    cfg.update(changes)
    cfg["updated_at"] = now_iso()
    _save_atomic(config_path(project_id), cfg)
    if "members" in changes or "name" in changes:
        from hydrahive.agents._workspace_links import sync_links_for_project
        sync_links_for_project(project_id)
    return cfg


def delete(project_id: str) -> bool:
    cfg = get(project_id)
    if not cfg:
        return False
    # Cascade: Project-Agent + Workspace + Project-Verzeichnis +
    # Server-Assignments (VMs/Container bleiben, project_id wird NULL).
    if cfg.get("agent_id"):
        agent_config.delete(cfg["agent_id"])
    from hydrahive.vms import db as vms_db
    from hydrahive.containers import db as containers_db
    from hydrahive.samba import disable_share as samba_disable
    from hydrahive.agents._workspace_links import sync_links_for_user
    affected_users = set(cfg.get("members", []))
    if cfg.get("created_by"):
        affected_users.add(cfg["created_by"])
    vms_db.clear_project_assignments(project_id)
    containers_db.clear_project_assignments(project_id)
    samba_disable(project_id)
    ws = settings.data_dir / "workspaces" / "projects" / project_id
    if ws.exists():
        shutil.rmtree(ws)
    pd = project_dir(project_id)
    if pd.exists():
        shutil.rmtree(pd)
    for user in affected_users:
        sync_links_for_user(user)
    logger.info("Projekt gelöscht: %s", project_id)
    return True
