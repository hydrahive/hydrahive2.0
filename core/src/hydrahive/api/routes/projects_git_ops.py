"""Git repo operations: commit, push, pull, delete."""
from __future__ import annotations

import shutil
from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._git_helpers import (
    GitCommit, err_to_code, project_or_404, repo_path_or_404, token_for,
)
from hydrahive.projects import config as project_config
from hydrahive.projects._git import ROOT_REPO
from hydrahive.projects._git_ops import commit_all, pull, push

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/{project_id}/git/repos/{repo_name}/commit")
def post_commit(
    project_id: str,
    repo_name: str,
    req: GitCommit,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    project_or_404(project_id, *auth)
    rp = repo_path_or_404(project_id, repo_name)
    ok, err = commit_all(rp, req.message,
                         author_name=username, author_email=f"{username}@hydrahive.local")
    if not ok:
        sc, code = err_to_code(err)
        raise coded(sc, code, detail=err)
    return {"ok": True}


@router.post("/{project_id}/git/repos/{repo_name}/push")
def post_push(
    project_id: str,
    repo_name: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = project_or_404(project_id, *auth)
    rp = repo_path_or_404(project_id, repo_name)
    ok, err = push(rp, token=token_for(p, repo_name))
    if not ok:
        sc, code = err_to_code(err)
        raise coded(sc, code, detail=err)
    return {"ok": True}


@router.post("/{project_id}/git/repos/{repo_name}/pull")
def post_pull(
    project_id: str,
    repo_name: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = project_or_404(project_id, *auth)
    rp = repo_path_or_404(project_id, repo_name)
    ok, err = pull(rp, token=token_for(p, repo_name))
    if not ok:
        sc, code = err_to_code(err)
        raise coded(sc, code, detail=err)
    return {"ok": True}


@router.delete("/{project_id}/git/repos/{repo_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repo(
    project_id: str,
    repo_name: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    p = project_or_404(project_id, *auth)
    if repo_name == ROOT_REPO:
        raise coded(400, "git_cannot_delete_root")
    rp = repo_path_or_404(project_id, repo_name)
    shutil.rmtree(rp, ignore_errors=True)
    repos = dict(p.get("git_repos", {}))
    repos.pop(repo_name, None)
    project_config.update(project_id, git_repos=repos)
