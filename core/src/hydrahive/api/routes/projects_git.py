"""Git-Routen pro Projekt — Multi-Repo (workspace/<repo-name>/.git/).

Read-only `GET .../git` (single Status) bleibt in routes/projects.py als Legacy.
Hier die neuen Multi-Repo-Endpoints unter `.../git/repos/...`."""
from __future__ import annotations

import shutil
from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._git_helpers import (
    GitCommit, GitRepoClone, GitRepoConfig, GitRepoInit,
    err_to_code, project_or_404, repo_path_or_404, token_for,
)
from hydrahive.projects import config as project_config
from hydrahive.projects._git import ROOT_REPO, init_repo, is_valid_name, list_repos
from hydrahive.projects._git_ops import clone_into, commit_all, pull, push, set_remote
from hydrahive.projects._paths import workspace_path

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/{project_id}/git/repos")
def get_repos(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    p = project_or_404(project_id, *auth)
    ws = workspace_path(project_id)
    repos = list_repos(ws)
    cfg_repos = p.get("git_repos", {})
    for r in repos:
        rc = cfg_repos.get(r["name"], {})
        r["has_token"] = bool(rc.get("git_token") or (r["name"] == ROOT_REPO and p.get("git_token")))
    return repos


@router.post("/{project_id}/git/repos/clone")
def post_clone(
    project_id: str,
    req: GitRepoClone,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = project_or_404(project_id, *auth)
    if not is_valid_name(req.name) or req.name == ROOT_REPO:
        raise coded(400, "git_invalid_repo_name", name=req.name)
    ok, err = clone_into(workspace_path(project_id), req.name, req.url, req.branch, req.token)
    if not ok:
        sc, code = err_to_code(err)
        raise coded(sc, code, detail=err)
    repos = dict(p.get("git_repos", {}))
    if req.token:
        repos[req.name] = {**repos.get(req.name, {}), "git_token": req.token}
    else:
        repos.setdefault(req.name, {})
    project_config.update(project_id, git_repos=repos, git_initialized=True)
    return {"ok": True}


@router.post("/{project_id}/git/repos/init")
def post_init(
    project_id: str,
    req: GitRepoInit,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = project_or_404(project_id, *auth)
    if not is_valid_name(req.name) or req.name == ROOT_REPO:
        raise coded(400, "git_invalid_repo_name", name=req.name)
    target = workspace_path(project_id) / req.name
    if target.exists():
        raise coded(409, "git_repo_exists", name=req.name)
    if not init_repo(target):
        raise coded(500, "git_failed", detail="init_failed")
    repos = dict(p.get("git_repos", {}))
    repos.setdefault(req.name, {})
    project_config.update(project_id, git_repos=repos, git_initialized=True)
    return {"ok": True}


@router.put("/{project_id}/git/repos/{repo_name}/config")
def put_repo_config(
    project_id: str,
    repo_name: str,
    req: GitRepoConfig,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = project_or_404(project_id, *auth)
    rp = repo_path_or_404(project_id, repo_name)
    if req.remote_url is not None:
        ok, err = set_remote(rp, req.remote_url)
        if not ok:
            sc, code = err_to_code(err)
            raise coded(sc, code, detail=err)
    if req.git_token is not None:
        repos = dict(p.get("git_repos", {}))
        existing = dict(repos.get(repo_name, {}))
        existing["git_token"] = req.git_token
        repos[repo_name] = existing
        project_config.update(project_id, git_repos=repos)
    return {"ok": True}


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
