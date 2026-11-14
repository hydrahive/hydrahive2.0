from __future__ import annotations

import logging
import secrets
from typing import Any

from hydrahive.agents import config as agent_config
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.projects import _validation
from hydrahive.projects import _members_model
from hydrahive.projects._delete import ProjectDeleteBlocked, delete  # noqa: F401 – öffentliche API
from hydrahive.projects._config_io import (
    _normalize, _save_atomic, get, list_all, list_for_user,
)
from hydrahive.projects._paths import (
    config_path,
    ensure_workspace,
    project_dir,
)

logger = logging.getLogger(__name__)

__all__ = ["get", "list_all", "list_for_user", "create", "update", "delete", "ProjectDeleteBlocked"]


def create(
    name: str,
    *,
    description: str = "",
    members: list[str] | None = None,
    llm_model: str,
    created_by: str,
    init_git: bool = False,
    metadata: dict | None = None,
    template: str | None = None,
) -> dict:
    _validation.validate_name(name)
    members = members or []
    _validation.validate_members(members)
    members = _members_model.normalize_members(members)

    from hydrahive.projects import _model_check
    warnings = _model_check.check(template)          # wirft vor dem ersten Ordner, wenn das Hauptmodell fehlt

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
        "webhook_secret": secrets.token_urlsafe(32),  # For secure webhook auth
    }
    project_dir(project_id).mkdir(parents=True, exist_ok=True)

    workspace = ensure_workspace(project_id)
    if init_git:
        from hydrahive.projects._git import init_repo
        cfg["git_initialized"] = init_repo(workspace)

    # Project-Agent automatisch anlegen
    # Template nur, wenn der Aufrufer es nennt (Route: immer). Module rufen bis Etappe 5 noch ohne Template und
    # setzen ihr Modell selbst – das bleibt bis dahin unverändert.
    try:
        agent = _create_agent(name, template, llm_model, created_by, project_id)
    except Exception:
        _remove_half_created(project_id)
        raise
    cfg["agent_id"] = agent["id"]
    _save_atomic(config_path(project_id), cfg)
    from hydrahive.agents._workspace_links import sync_links_for_project
    sync_links_for_project(project_id)
    logger.info("Projekt '%s' angelegt (id=%s, agent=%s)", name, project_id, agent["id"])
    return {**cfg, "warnings": warnings}


def _create_agent(name: str, template: str | None, llm_model: str, created_by: str, project_id: str) -> dict:
    from hydrahive.agents._binding import template_if_available
    return agent_config.create(
        agent_type="project",
        name=f"{name} — Projekt-Agent",
        template=template_if_available(template) if template else None,
        llm_model=llm_model,
        owner=created_by,
        created_by=created_by,
        description=f"Auto-erstellt für Projekt '{name}'",
        project_id=project_id,
        temperature=1.0,
        max_tokens=16000,
        thinking_budget=0,
    )


def _remove_half_created(project_id: str) -> None:
    """Agent scheiterte: die gerade angelegten Ordner wieder weg – nur wenn leer (kein rmtree, nichts Fremdes)."""
    from hydrahive.projects._paths import workspace_path
    for d in (project_dir(project_id), workspace_path(project_id)):
        try:
            if d.is_dir() and not d.is_symlink():
                d.rmdir()
        except OSError as exc:
            logger.warning("Halb angelegtes Projekt %s: %s nicht entfernt: %s", project_id, d, exc)


def update(project_id: str, **changes: Any) -> dict:
    cfg = get(project_id)
    if not cfg:
        raise KeyError(f"Projekt '{project_id}' nicht gefunden")
    # execution nur über projects/execution.py (Admin/Kern-Funktion, mit Prüfung und Protokoll)
    for protected in ("id", "agent_id", "created_at", "created_by", "execution"):
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
    if "name" in changes:
        from hydrahive.projects._linked import sync_pointing_to
        sync_pointing_to(project_id)            # linked/<Name> anderer Projekte (linked-projects.md)
    return cfg
