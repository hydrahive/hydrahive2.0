"""Shared helpers + Pydantic models für Git-Routes."""
from __future__ import annotations

from fastapi import status
from pydantic import BaseModel

from hydrahive.api.middleware.errors import coded
from hydrahive.projects import config as project_config
from hydrahive.projects._git import ROOT_REPO, is_valid_name, repo_path_for
from hydrahive.projects._paths import workspace_path


class GitRepoConfig(BaseModel):
    remote_url: str | None = None
    git_token: str | None = None


class GitRepoClone(BaseModel):
    name: str
    url: str
    branch: str | None = None
    token: str | None = None


class GitRepoInit(BaseModel):
    name: str


class GitCommit(BaseModel):
    message: str


def project_or_404(project_id: str, username: str, role: str) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    if role != "admin" and username not in p.get("members", []) and p.get("created_by") != username:
        raise coded(status.HTTP_403_FORBIDDEN, "project_no_access")
    return p


def repo_path_or_404(project_id: str, repo_name: str):
    if not is_valid_name(repo_name):
        raise coded(status.HTTP_400_BAD_REQUEST, "git_invalid_repo_name", name=repo_name)
    rp = repo_path_for(workspace_path(project_id), repo_name)
    if rp is None or not (rp / ".git").exists():
        raise coded(status.HTTP_404_NOT_FOUND, "git_repo_not_found", name=repo_name)
    return rp


def err_to_code(err: str) -> tuple[int, str]:
    mapping = {
        "repo_exists": (409, "git_repo_exists"),
        "no_changes": (400, "git_no_changes"),
        "no_remote": (400, "git_no_remote"),
        "no_repo": (400, "git_no_repo"),
        "empty_message": (400, "git_empty_message"),
        "timeout": (504, "git_timeout"),
    }
    return mapping.get(err, (500, "git_failed"))


def token_for(project: dict, repo_name: str) -> str | None:
    repo_cfg = project.get("git_repos", {}).get(repo_name) or {}
    if repo_cfg.get("git_token"):
        return repo_cfg["git_token"]
    if repo_name == ROOT_REPO and project.get("git_token"):
        return project["git_token"]
    return None
