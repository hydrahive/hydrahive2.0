from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import (
    ProjectCreate, ProjectUpdate, check_project_access,
)
from hydrahive.projects import ProjectValidationError, config as project_config
from hydrahive.projects import audit as project_audit
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


@router.patch("/{project_id}")
def update_project(
    project_id: str,
    req: ProjectUpdate,
    auth: Annotated[tuple[str, str], Depends(require_admin)],
) -> dict:
    changes = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        result = project_config.update(project_id, **changes)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    except ProjectValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))
    project_audit.log(project_id, auth[0], "project_updated", details=changes)
    return result


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_project(project_id: str) -> None:
    if not project_config.delete(project_id):
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")



@router.post("/{project_id}/members/{username}")
def add_member(
    project_id: str,
    username: str,
    auth: Annotated[tuple[str, str], Depends(require_admin)],
) -> dict:
    try:
        result = project_members.add(project_id, username)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    except ProjectValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))
    project_audit.log(project_id, auth[0], "member_added", target=username)
    return result


@router.delete("/{project_id}/members/{username}")
def remove_member(
    project_id: str,
    username: str,
    auth: Annotated[tuple[str, str], Depends(require_admin)],
) -> dict:
    try:
        result = project_members.remove(project_id, username)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    project_audit.log(project_id, auth[0], "member_removed", target=username)
    return result


@router.get("/{project_id}/audit")
def get_project_audit(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    action: str | None = None,
    user: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict:
    """Audit-Spur eines Projekts (#74). Sichtbar für Projekt-Zugriffsberechtigte."""
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    _check_access(p, *auth)
    from hydrahive.projects import audit as project_audit
    entries = project_audit.list_for_project(project_id, action=action, user_id=user, limit=limit)
    return {"entries": entries, "count": len(entries)}


