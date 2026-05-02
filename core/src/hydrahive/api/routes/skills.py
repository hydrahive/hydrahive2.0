"""Skill-CRUD-Endpoints.

Scopes:
- system  : nur Admin schreibt/löscht, alle lesen
- user    : Owner == username (auth)
- agent   : Owner == agent_id, Auth-Check über Agent-Owner

Listing für einen Agent ruft list_for_agent (merge system+user+agent).
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._skill_route_helpers import (
    SkillBody, SkillSourceBody, check_agent_access as _check_agent_access,
    serialize_skill as _serialize,
)
from hydrahive.skills import delete_skill, get_skill, list_for_agent, save_skill
from hydrahive.skills.loader import _list_dir
from hydrahive.skills._paths import system_dir, user_dir
from hydrahive.skills.models import Skill, SkillScope, SkillSource, is_valid_name

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
def list_skills_endpoint(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    agent_id: str | None = None,
    scope: Literal["system", "user", "agent", "all"] = "all",
) -> list[dict]:
    """Wenn agent_id gesetzt: gemergte Liste für diesen Agent (system+user+agent).
    Sonst: filterbar nach scope."""
    username, role = auth
    if agent_id:
        agent = _check_agent_access(agent_id, username, role)
        disabled = list(agent.get("disabled_skills", []))
        return [_serialize(s) for s in list_for_agent(agent_id, agent["owner"] or username, disabled=disabled)]
    out: list[Skill] = []
    if scope in ("system", "all"):
        out.extend(_list_dir(system_dir(), "system", "system"))
    if scope in ("user", "all"):
        out.extend(_list_dir(user_dir(username), "user", username))
    return [_serialize(s) for s in out]


@router.get("/{scope}/{name}")
def get_skill_endpoint(
    scope: SkillScope,
    name: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    owner: str | None = None,
) -> dict:
    username, role = auth
    if scope == "user" and not owner:
        owner = username
    if scope == "system":
        owner = "system"
    if scope == "user" and owner != username and role != "admin":
        raise coded(status.HTTP_403_FORBIDDEN, "skill_no_access")
    if scope == "agent":
        if not owner:
            raise coded(status.HTTP_400_BAD_REQUEST, "skill_owner_required")
        _check_agent_access(owner, username, role)
    s = get_skill(scope, owner or "", name)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "skill_not_found", name=name)
    return _serialize(s)


@router.post("/{scope}", status_code=status.HTTP_201_CREATED)
def create_or_update(
    scope: SkillScope,
    req: SkillBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    owner: str | None = None,
) -> dict:
    username, role = auth
    if not is_valid_name(req.name):
        raise coded(status.HTTP_400_BAD_REQUEST, "skill_name_invalid", name=req.name)
    if scope == "system":
        if role != "admin":
            raise coded(status.HTTP_403_FORBIDDEN, "admin_only")
        owner = "system"
    elif scope == "user":
        owner = username if not owner or role != "admin" else owner
    elif scope == "agent":
        if not owner:
            raise coded(status.HTTP_400_BAD_REQUEST, "skill_owner_required")
        _check_agent_access(owner, username, role)
    skill = Skill(
        name=req.name, description=req.description, when_to_use=req.when_to_use,
        tools_required=list(req.tools_required), body=req.body,
        sources=[SkillSource(url=s.url, auth=s.auth, description=s.description)
                 for s in req.sources if s.url],
        scope=scope, owner=owner or "",
    )
    ok, err = save_skill(skill)
    if not ok:
        raise coded(status.HTTP_400_BAD_REQUEST, err or "skill_save_failed")
    return _serialize(skill)


@router.delete("/{scope}/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill_endpoint(
    scope: SkillScope,
    name: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    owner: str | None = None,
) -> None:
    username, role = auth
    if scope == "system":
        if role != "admin":
            raise coded(status.HTTP_403_FORBIDDEN, "admin_only")
        owner = "system"
    elif scope == "user":
        owner = username if not owner or role != "admin" else owner
    elif scope == "agent":
        if not owner:
            raise coded(status.HTTP_400_BAD_REQUEST, "skill_owner_required")
        _check_agent_access(owner, username, role)
    if not delete_skill(scope, owner or "", name):
        raise coded(status.HTTP_404_NOT_FOUND, "skill_not_found", name=name)
