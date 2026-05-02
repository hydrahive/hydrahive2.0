from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import (
    ProjectCreate, ProjectUpdate, check_project_access,
)
from hydrahive.projects import ProjectValidationError, config as project_config
from hydrahive.projects import members as project_members

router = APIRouter(prefix="/api/projects", tags=["projects"])
_check_access = check_project_access


@router.get("")
def list_projects(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    username, role = auth
    if role == "admin":
        return project_config.list_all()
    return project_config.list_for_user(username)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    req: ProjectCreate,
    auth: Annotated[tuple[str, str], Depends(require_admin)],
) -> dict:
    creator, _ = auth
    try:
        return project_config.create(
            name=req.name,
            description=req.description,
            members=req.members,
            llm_model=req.llm_model,
            created_by=creator,
            init_git=req.init_git,
        )
    except ProjectValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))


@router.get("/{project_id}")
def get_project(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    _check_access(p, *auth)
    return p


@router.patch("/{project_id}", dependencies=[Depends(require_admin)])
def update_project(project_id: str, req: ProjectUpdate) -> dict:
    changes = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        return project_config.update(project_id, **changes)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    except ProjectValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_project(project_id: str) -> None:
    if not project_config.delete(project_id):
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")



@router.post("/{project_id}/members/{username}", dependencies=[Depends(require_admin)])
def add_member(project_id: str, username: str) -> dict:
    try:
        return project_members.add(project_id, username)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    except ProjectValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))


@router.delete("/{project_id}/members/{username}", dependencies=[Depends(require_admin)])
def remove_member(project_id: str, username: str) -> dict:
    try:
        return project_members.remove(project_id, username)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")


