"""Workspace-File-Browser für Projekte — Write/Upload/Delete-Endpunkte."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import (
    check_project_access, is_text_file, safe_workspace_path,
)
from hydrahive.projects import config as project_config
from hydrahive.projects._paths import workspace_path

router = APIRouter(prefix="/api/projects", tags=["projects"])

MAX_WRITE_BYTES = 1 * 1024 * 1024     # 1 MB
MAX_UPLOAD_BYTES = 10 * 1024 * 1024   # 10 MB


class _WriteBody(BaseModel):
    path: str = Field(..., min_length=1)
    content: str


@router.post("/{project_id}/files/write")
def write_file(
    project_id: str,
    body: _WriteBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(p, *auth)

    workspace = workspace_path(project_id)
    target = safe_workspace_path(workspace, body.path)

    if not is_text_file(target):
        raise coded(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "binary_file")

    data = body.content.encode("utf-8")
    if len(data) > MAX_WRITE_BYTES:
        raise coded(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")

    if target.exists() and target.is_dir():
        raise coded(status.HTTP_400_BAD_REQUEST, "is_directory")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)

    return {"ok": True, "size": len(data)}


@router.post("/{project_id}/files/upload")
async def upload_file(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    file: UploadFile = File(...),
    path: str = Query(default=""),
) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(p, *auth)

    name = (file.filename or "upload").strip()
    if not name or "/" in name or "\\" in name:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_filename")

    workspace = workspace_path(project_id)
    rel = f"{path}/{name}" if path else name
    target = safe_workspace_path(workspace, rel)

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise coded(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)

    return {"ok": True, "name": name, "size": len(data)}


@router.delete("/{project_id}/files")
def delete_file(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    path: str = Query(...),
) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(p, *auth)

    workspace = workspace_path(project_id)
    target = safe_workspace_path(workspace, path)

    if target == workspace.resolve():
        raise coded(status.HTTP_400_BAD_REQUEST, "cannot_delete_workspace")
    if not target.exists():
        raise coded(status.HTTP_404_NOT_FOUND, "file_not_found")
    if target.is_dir():
        raise coded(status.HTTP_400_BAD_REQUEST, "is_directory")

    target.unlink()
    return {"ok": True}
