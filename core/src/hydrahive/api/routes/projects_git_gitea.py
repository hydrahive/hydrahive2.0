"""Lokaler Gitea-Flow für Projekt-Repos."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._git_helpers import err_to_code, project_or_404, repo_path_or_404
from hydrahive.projects import _gitea

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _require_project_admin(project: dict, username: str, role: str) -> None:
    if role == "admin" or project.get("created_by") == username:
        return
    raise coded(403, "project_admin_required")


@router.get("/{project_id}/git/repos/{repo_name}/gitea")
def get_gitea_status(
    project_id: str,
    repo_name: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    project_or_404(project_id, *auth)
    repo_path = repo_path_or_404(project_id, repo_name)
    return _gitea.status(project_id, repo_name, repo_path)


@router.post("/{project_id}/git/repos/{repo_name}/gitea/create")
def create_gitea_repo(
    project_id: str,
    repo_name: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, role = auth
    project = project_or_404(project_id, username, role)
    _require_project_admin(project, username, role)
    repo_path = repo_path_or_404(project_id, repo_name)
    ok, err, status = _gitea.create_repo_and_remote(project_id, repo_name, repo_path)
    if not ok:
        sc, code = err_to_code(err)
        raise coded(sc, code)
    return {"ok": True, "status": status}


@router.post("/{project_id}/git/repos/{repo_name}/gitea/push")
def push_gitea_repo(
    project_id: str,
    repo_name: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    project_or_404(project_id, *auth)
    repo_path = repo_path_or_404(project_id, repo_name)
    ok, err = _gitea.push_remote(repo_path)
    if not ok:
        sc, code = err_to_code(err)
        raise coded(sc, code)
    return {"ok": True}


@router.post("/{project_id}/git/repos/{repo_name}/gitea/pull")
def pull_gitea_repo(
    project_id: str,
    repo_name: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    project_or_404(project_id, *auth)
    repo_path = repo_path_or_404(project_id, repo_name)
    ok, err = _gitea.pull_remote(repo_path)
    if not ok:
        sc, code = err_to_code(err)
        raise coded(sc, code)
    return {"ok": True}
