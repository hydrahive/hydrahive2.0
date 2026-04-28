from __future__ import annotations

from pathlib import Path

from hydrahive.settings import settings


def projects_root() -> Path:
    return settings.data_dir / "projects"


def project_dir(project_id: str) -> Path:
    return projects_root() / project_id


def config_path(project_id: str) -> Path:
    return project_dir(project_id) / "config.json"


def workspace_path(project_id: str) -> Path:
    return settings.data_dir / "workspaces" / "projects" / project_id


def ensure_workspace(project_id: str) -> Path:
    p = workspace_path(project_id)
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()
