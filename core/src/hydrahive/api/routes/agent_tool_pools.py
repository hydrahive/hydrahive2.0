"""Freigabe-Pools des Tool-Katalogs (Spec E1/E3/E5/S5): Agenten-Pool, Projekt-Pool, Besitzer-Freigabe.

Die Identität kommt immer aus dem Token (require_auth/require_admin), nie aus dem Body; ``items`` ist das einzige Feld.
Die Regeln selbst stehen in ``agents/tool_pools.py`` (PermissionError → 403, ValueError → 400, KeyError → 404).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.agents import config as agent_config
from hydrahive.agents import tool_pools
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._agent_schemas import check_agent_access
from hydrahive.api.routes._project_route_helpers import check_project_access
from hydrahive.projects import config as project_config

router = APIRouter(tags=["tool-pools"])
Auth = Annotated[tuple[str, str], Depends(require_auth)]


class PoolBody(BaseModel):
    items: list[str] = Field(default_factory=list, max_length=tool_pools.MAX_ITEMS)


def _forbidden(exc: PermissionError):
    return coded(status.HTTP_403_FORBIDDEN, "tool_pool_forbidden", message=str(exc))


def _invalid(exc: ValueError):
    return coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(exc))


@router.get("/api/agents/{agent_id}/tool-pool")
def get_agent_pool(agent_id: str, auth: Auth) -> dict:
    agent = agent_config.get(agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    check_agent_access(agent, *auth)
    return {"items": tool_pools.agent_pool_items(agent_id), "effective": tool_pools.tool_pool_for(agent, None)}


@router.put("/api/agents/{agent_id}/tool-pool")
def put_agent_pool(agent_id: str, body: PoolBody, auth: Auth) -> dict:
    username, _ = auth
    try:
        return {"items": tool_pools.set_agent_pool(username, agent_id, body.items)}
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    except PermissionError as exc:
        raise _forbidden(exc)
    except ValueError as exc:
        raise _invalid(exc)


@router.get("/api/projects/{project_id}/tool-pool")
def get_project_pool(project_id: str, auth: Auth) -> dict:
    project = project_config.get(project_id)
    if not project:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    username, role = auth
    check_project_access(project, username, role, required="read")
    return {"items": tool_pools.project_pool_items(project_id)}


@router.put("/api/projects/{project_id}/tool-pool")
def put_project_pool(project_id: str, body: PoolBody, auth: Auth) -> dict:
    username, _ = auth
    try:
        return {"items": tool_pools.set_project_pool(username, project_id, body.items)}
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    except PermissionError as exc:
        raise _forbidden(exc)
    except ValueError as exc:
        raise _invalid(exc)


@router.get("/api/admin/tool-grants/{username}")
def get_owner_grants(username: str, _: Annotated[tuple[str, str], Depends(require_admin)]) -> dict:
    return {"items": tool_pools.owner_grants(username)}


@router.put("/api/admin/tool-grants/{username}")
def put_owner_grants(username: str, body: PoolBody, auth: Annotated[tuple[str, str], Depends(require_admin)]) -> dict:
    admin, _ = auth
    try:
        return {"items": tool_pools.set_owner_grants(admin, username, body.items)}
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "user_not_found")
    except PermissionError as exc:
        raise _forbidden(exc)
    except ValueError as exc:
        raise _invalid(exc)
