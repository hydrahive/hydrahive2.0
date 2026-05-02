from __future__ import annotations

from fastapi import status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.errors import coded


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    members: list[str] = []
    llm_model: str
    init_git: bool = False


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    members: list[str] | None = None


def check_project_access(project: dict, username: str, role: str) -> None:
    if role == "admin":
        return
    if username in project.get("members", []) or project.get("created_by") == username:
        return
    raise coded(status.HTTP_403_FORBIDDEN, "project_no_access")
