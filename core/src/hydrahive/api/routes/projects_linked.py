"""Verknüpfte Projekte einstellen (docs/specs/linked-projects.md).

PUT /api/projects/{id}/linked-projects {"projects": [...]} – Admin im Projekt UND ≥ write in jedem verknüpften Projekt
(System-Admin immer). Jede Änderung → Projekt-Audit ``linked_projects_changed``.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.projects import _linked
from hydrahive.projects import audit as project_audit
from hydrahive.projects import config as project_config
from hydrahive.projects.public_view import public_view

router = APIRouter(prefix="/api/projects", tags=["projects"])

_STATUS = {"project_not_found": status.HTTP_404_NOT_FOUND, "project_admin_required": status.HTTP_403_FORBIDDEN,
           "linked_project_no_access": status.HTTP_403_FORBIDDEN, "linked_projects_invalid": status.HTTP_400_BAD_REQUEST}


class LinkedIn(BaseModel):
    projects: list[str] = Field(max_length=_linked.MAX_LINKS + 1)


@router.put("/{project_id}/linked-projects")
def set_linked_projects(project_id: str, body: LinkedIn,
                        auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    before = (project_config.get(project_id) or {}).get("linked_projects") or []
    try:
        links = _linked.set_links(project_id, body.projects, username=auth[0], role=auth[1])
    except _linked.LinkError as e:
        extra = {"project": e.project} if e.project else {}
        raise coded(_STATUS.get(e.code, status.HTTP_400_BAD_REQUEST), e.code, **extra) from None
    project_audit.log(project_id, auth[0], "linked_projects_changed",
                      details={"before": before, "projects": links})
    return public_view(project_config.get(project_id))
