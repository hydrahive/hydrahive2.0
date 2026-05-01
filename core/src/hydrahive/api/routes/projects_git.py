"""Git-Schreib-Operationen pro Projekt — Clone/Commit/Push/Pull/Remote.

Read-only `GET .../git` bleibt in routes/projects.py. Diese Datei deckt nur
die schreibenden Aktionen ab — sonst würde projects.py zu groß (CLAUDE.md
~150-Zeilen-Regel)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.projects import config as project_config
from hydrahive.projects._git import init_repo
from hydrahive.projects._git_ops import (
    clone_repo,
    commit_all,
    pull,
    push,
    set_remote,
)
from hydrahive.projects._paths import workspace_path

router = APIRouter(prefix="/api/projects", tags=["projects"])


class GitConfigUpdate(BaseModel):
    remote_url: str | None = None
    git_token: str | None = None


class GitClone(BaseModel):
    url: str
    branch: str | None = None


class GitCommit(BaseModel):
    message: str


def _project_or_404(project_id: str, username: str, role: str) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    if role != "admin" and username not in p.get("members", []) and p.get("created_by") != username:
        raise coded(status.HTTP_403_FORBIDDEN, "project_no_access")
    return p


def _err_to_code(err: str) -> tuple[int, str]:
    if err == "workspace_not_empty":
        return 409, "git_workspace_not_empty"
    if err == "no_changes":
        return 400, "git_no_changes"
    if err == "no_remote":
        return 400, "git_no_remote"
    if err == "empty_message":
        return 400, "git_empty_message"
    if err == "timeout":
        return 504, "git_timeout"
    return 500, "git_failed"


@router.put("/{project_id}/git/config")
def put_git_config(
    project_id: str,
    req: GitConfigUpdate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = _project_or_404(project_id, *auth)
    changes: dict = {}
    if req.git_token is not None:
        changes["git_token"] = req.git_token
    if req.remote_url is not None:
        ok, err = set_remote(workspace_path(project_id), req.remote_url)
        if not ok:
            sc, code = _err_to_code(err)
            raise coded(sc, code, detail=err)
    if changes:
        project_config.update(project_id, **changes)
    return {"ok": True}


@router.post("/{project_id}/git/init")
def post_git_init(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = _project_or_404(project_id, *auth)
    ws = workspace_path(project_id)
    if init_repo(ws):
        project_config.update(project_id, git_initialized=True)
        return {"ok": True}
    raise coded(500, "git_failed", detail="init_failed")


@router.post("/{project_id}/git/clone")
def post_git_clone(
    project_id: str,
    req: GitClone,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = _project_or_404(project_id, *auth)
    ws = workspace_path(project_id)
    ok, err = clone_repo(ws, req.url, req.branch, p.get("git_token") or None)
    if not ok:
        sc, code = _err_to_code(err)
        raise coded(sc, code, detail=err)
    project_config.update(project_id, git_initialized=True)
    return {"ok": True}


@router.post("/{project_id}/git/commit")
def post_git_commit(
    project_id: str,
    req: GitCommit,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    p = _project_or_404(project_id, *auth)
    ok, err = commit_all(
        workspace_path(project_id), req.message,
        author_name=username, author_email=f"{username}@hydrahive.local",
    )
    if not ok:
        sc, code = _err_to_code(err)
        raise coded(sc, code, detail=err)
    return {"ok": True}


@router.post("/{project_id}/git/push")
def post_git_push(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = _project_or_404(project_id, *auth)
    ok, err = push(workspace_path(project_id), token=p.get("git_token") or None)
    if not ok:
        sc, code = _err_to_code(err)
        raise coded(sc, code, detail=err)
    return {"ok": True}


@router.post("/{project_id}/git/pull")
def post_git_pull(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = _project_or_404(project_id, *auth)
    ok, err = pull(workspace_path(project_id), token=p.get("git_token") or None)
    if not ok:
        sc, code = _err_to_code(err)
        raise coded(sc, code, detail=err)
    return {"ok": True}
