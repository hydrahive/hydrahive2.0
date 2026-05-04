"""Workspace-File-Browser für Projekte — Read-Endpunkte."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import PlainTextResponse

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import (
    check_project_access, is_text_file, safe_workspace_path,
)
from hydrahive.projects import config as project_config
from hydrahive.projects._paths import workspace_path

router = APIRouter(prefix="/api/projects", tags=["projects"])

_MAX_READ = 100 * 1024  # 100 KB


@router.get("/{project_id}/files")
def list_files(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    path: str = Query(default=""),
) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(p, *auth)

    workspace = workspace_path(project_id)
    target = safe_workspace_path(workspace, path)

    if not target.exists():
        raise coded(status.HTTP_404_NOT_FOUND, "path_not_found")
    if not target.is_dir():
        raise coded(status.HTTP_400_BAD_REQUEST, "not_a_directory")

    entries = []
    for item in sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
        entries.append({
            "name": item.name,
            "type": "file" if item.is_file() else "dir",
            "size": item.stat().st_size if item.is_file() else None,
            "modified": item.stat().st_mtime,
        })

    rel = str(target.relative_to(workspace.resolve()))
    return {"path": "" if rel == "." else rel, "entries": entries}


@router.get("/{project_id}/files/read")
def read_file(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    path: str = Query(...),
) -> PlainTextResponse:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(p, *auth)

    workspace = workspace_path(project_id)
    target = safe_workspace_path(workspace, path)

    if not target.exists() or not target.is_file():
        raise coded(status.HTTP_404_NOT_FOUND, "file_not_found")

    if not is_text_file(target):
        raise coded(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "binary_file")

    content = target.read_bytes()[:_MAX_READ].decode("utf-8", errors="replace")
    return PlainTextResponse(content)
