from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.agents import AgentValidationError, config as agent_config, external_instances as ei
from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes import _delete_job

router = APIRouter(prefix="/api/external-instances", tags=["external-instances"])


class InstanceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    llm_model: str


@router.get("", dependencies=[Depends(require_admin)])
def list_external_instances() -> list[dict]:
    return ei.list_instances()


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_external_instance(req: InstanceCreate) -> dict:
    try:
        return ei.create_instance(req.name.strip(), req.llm_model)
    except AgentValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))
    except ValueError:
        raise coded(status.HTTP_409_CONFLICT, "username_exists")


@router.delete("/{agent_id}", status_code=status.HTTP_202_ACCEPTED)
def delete_external_instance(agent_id: str, admin: Annotated[tuple[str, str], Depends(require_admin)],
                             mode: str | None = None, confirm: str | None = None):
    """Agent + Instanz-Nutzer ins Archiv oder unwiderruflich (archiv-system.md, Etappe 2). Schlüssel werden ungültig."""
    try:
        agent = agent_config.get(agent_id)
    except ValueError:
        agent = None
    if not agent or not agent.get("external"):
        raise coded(status.HTTP_404_NOT_FOUND, "instance_not_found")
    return _delete_job.start("instance", agent_id, agent.get("name") or agent_id, mode, confirm, admin[0])


@router.post("/{agent_id}/rotate-key", dependencies=[Depends(require_admin)])
def rotate_external_instance_key(agent_id: str) -> dict:
    key = ei.rotate_key(agent_id)
    if key is None:
        raise coded(status.HTTP_404_NOT_FOUND, "instance_not_found")
    return {"api_key": key}
