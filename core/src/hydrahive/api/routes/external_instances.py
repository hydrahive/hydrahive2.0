from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.agents import external_instances as ei
from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded

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
    except ValueError:
        raise coded(status.HTTP_409_CONFLICT, "username_exists")


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_external_instance(agent_id: str) -> None:
    if not ei.delete_instance(agent_id):
        raise coded(status.HTTP_404_NOT_FOUND, "instance_not_found")


@router.post("/{agent_id}/rotate-key", dependencies=[Depends(require_admin)])
def rotate_external_instance_key(agent_id: str) -> dict:
    key = ei.rotate_key(agent_id)
    if key is None:
        raise coded(status.HTTP_404_NOT_FOUND, "instance_not_found")
    return {"api_key": key}
