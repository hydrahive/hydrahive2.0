from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive import media_projects
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import check_project_access
from hydrahive.projects import config as project_config

router = APIRouter(prefix="/api/projects/{project_id}/media-projects", tags=["media-projects"])


class MediaProjectCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)


class MediaProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)


def _authorize(project_id: str, auth: tuple[str, str]) -> None:
    project = project_config.get(project_id)
    if not project:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(project, *auth)


@router.get("")
def list_media_projects(project_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    _authorize(project_id, auth)
    return media_projects.list_all(project_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_media_project(project_id: str, body: MediaProjectCreate, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _authorize(project_id, auth)
    try:
        return media_projects.create(project_id, body.slug, body.name, body.description)
    except FileExistsError:
        raise coded(status.HTTP_409_CONFLICT, "media_project_exists")
    except media_projects.MediaProjectError:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_media_project")


@router.get("/{slug}")
def get_media_project(project_id: str, slug: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _authorize(project_id, auth)
    try:
        result = media_projects.get(project_id, slug)
    except media_projects.MediaProjectError:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_media_project")
    if result is None:
        raise coded(status.HTTP_404_NOT_FOUND, "media_project_not_found")
    return result


@router.patch("/{slug}")
def update_media_project(project_id: str, slug: str, body: MediaProjectUpdate, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _authorize(project_id, auth)
    try:
        return media_projects.update(project_id, slug, **body.model_dump(exclude_unset=True))
    except FileNotFoundError:
        raise coded(status.HTTP_404_NOT_FOUND, "media_project_not_found")
    except media_projects.MediaProjectError:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_media_project")


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media_project(project_id: str, slug: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> None:
    _authorize(project_id, auth)
    try:
        deleted = media_projects.delete(project_id, slug)
    except media_projects.MediaProjectError:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_media_project")
    if not deleted:
        raise coded(status.HTTP_404_NOT_FOUND, "media_project_not_found")
