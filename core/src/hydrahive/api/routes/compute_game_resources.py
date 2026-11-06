"""Core API for project-bound Game Studio resources and isolation approvals."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal, require_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._compute_game_resource_schemas import GameResourceCreate, IsolationApprovalCreate
from hydrahive.api.routes._project_route_helpers import check_project_access
from hydrahive.compute import game_resources
from hydrahive.projects import config as project_config

router = APIRouter(prefix="/api/compute", tags=["compute", "game-studio"])


def _project(project_id: str, principal: AuthPrincipal, required: str) -> dict:
    project = project_config.get(project_id)
    if project is None:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(project, principal.username, principal.role, required=required)
    return project


def _raise_store_error(exc: game_resources.GameResourceError) -> None:
    if exc.code.endswith("_not_found"):
        raise coded(status.HTTP_404_NOT_FOUND, exc.code)
    raise coded(status.HTTP_409_CONFLICT, exc.code)


@router.get("/game-isolation-approvals")
def list_game_isolation_approvals(
    principal: Annotated[AuthPrincipal, Depends(require_admin_principal)],
    node_id: str | None = Query(default=None, max_length=128),
) -> list[dict]:
    return [asdict(item) for item in game_resources.list_isolation_approvals(node_id=node_id)]


@router.post("/game-isolation-approvals", status_code=status.HTTP_201_CREATED)
def create_game_isolation_approval(
    body: IsolationApprovalCreate,
    principal: Annotated[AuthPrincipal, Depends(require_admin_principal)],
) -> dict:
    try:
        approval = game_resources.approve_isolation(
            node_id=body.node_id,
            isolation_profile_id=body.isolation_profile_id,
            runner_version=body.runner_version,
            policy_digest=body.policy_digest,
            proof_digest=body.proof_digest,
            approved_by=principal.user_id,
        )
    except game_resources.GameResourceError as exc:
        _raise_store_error(exc)
    except sqlite3.IntegrityError:
        raise coded(status.HTTP_409_CONFLICT, "game_isolation_approval_exists")
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, "game_isolation_approval_invalid", reason=str(exc))
    return asdict(approval)


@router.delete("/game-isolation-approvals/{approval_id}")
def revoke_game_isolation_approval(
    approval_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_admin_principal)],
) -> dict:
    try:
        return asdict(
            game_resources.revoke_isolation_approval(
                approval_id,
                revoked_by=principal.user_id,
            )
        )
    except game_resources.GameResourceError as exc:
        _raise_store_error(exc)
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, "game_isolation_approval_invalid", reason=str(exc))


@router.get("/projects/{project_id}/game-resources")
def list_project_game_resources(
    project_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> list[dict]:
    _project(project_id, principal, "read")
    return [asdict(item) for item in game_resources.list_workspaces(project_id)]


@router.post("/projects/{project_id}/game-resources", status_code=status.HTTP_201_CREATED)
def create_project_game_resource(
    project_id: str,
    body: GameResourceCreate,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    _project(project_id, principal, "admin")
    try:
        workspace = game_resources.create_workspace(
            project_id=project_id,
            node_id=body.node_id,
            workspace_handle=body.workspace_handle,
            engine=body.engine,
            engine_version=body.engine_version,
            engine_project_relpath=body.engine_project_relpath,
            trust_mode=body.trust_mode,
            isolation_approval_id=body.isolation_approval_id,
            isolation_profile_id=body.isolation_profile_id,
            runner_version=body.runner_version,
            policy_digest=body.policy_digest,
            created_by=principal.user_id,
        )
    except game_resources.GameResourceError as exc:
        _raise_store_error(exc)
    except sqlite3.IntegrityError:
        raise coded(status.HTTP_409_CONFLICT, "game_resource_conflict")
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, "game_resource_invalid", reason=str(exc))
    return asdict(workspace)


@router.get("/projects/{project_id}/game-resources/{resource_id}")
def get_project_game_resource(
    project_id: str,
    resource_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    _project(project_id, principal, "read")
    workspace = game_resources.get_workspace(project_id, resource_id)
    if workspace is None:
        raise coded(status.HTTP_404_NOT_FOUND, "game_resource_not_found")
    return asdict(workspace)


@router.post("/projects/{project_id}/game-resources/{resource_id}/rotate")
def rotate_project_game_resource(
    project_id: str,
    resource_id: str,
    body: GameResourceCreate,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    _project(project_id, principal, "admin")
    current = game_resources.get_workspace(project_id, resource_id)
    if current is None:
        raise coded(status.HTTP_404_NOT_FOUND, "game_resource_not_found")
    if body.node_id != current.node_id:
        raise coded(status.HTTP_409_CONFLICT, "game_execution_binding_mismatch")
    try:
        rotated = game_resources.rotate_workspace(
            project_id=project_id,
            resource_id=resource_id,
            workspace_handle=body.workspace_handle,
            engine=body.engine,
            engine_version=body.engine_version,
            engine_project_relpath=body.engine_project_relpath,
            trust_mode=body.trust_mode,
            isolation_approval_id=body.isolation_approval_id,
            isolation_profile_id=body.isolation_profile_id,
            runner_version=body.runner_version,
            policy_digest=body.policy_digest,
            actor=principal.user_id,
        )
    except game_resources.GameResourceError as exc:
        _raise_store_error(exc)
    except sqlite3.IntegrityError:
        raise coded(status.HTTP_409_CONFLICT, "game_resource_conflict")
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, "game_resource_invalid", reason=str(exc))
    return asdict(rotated)


@router.delete("/projects/{project_id}/game-resources/{resource_id}")
def revoke_project_game_resource(
    project_id: str,
    resource_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    _project(project_id, principal, "admin")
    try:
        return asdict(
            game_resources.revoke_workspace(
                project_id=project_id,
                resource_id=resource_id,
                actor=principal.user_id,
            )
        )
    except game_resources.GameResourceError as exc:
        _raise_store_error(exc)
