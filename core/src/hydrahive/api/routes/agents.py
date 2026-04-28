from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_admin, require_auth

router = APIRouter(prefix="/api/agents", tags=["agents"])


class CreateSpecialistRequest(BaseModel):
    name: str
    domain: str
    llm_model: str
    tools: list[str] = []
    execution_mode: str | None = None


@router.get("")
def list_agents(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    username, role = auth
    if role == "admin":
        return agent_config.list_all()
    return agent_config.list_by_owner(username)


@router.get("/{agent_id}")
def get_agent(
    agent_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, role = auth
    agent = agent_config.get(agent_id)
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent nicht gefunden")
    if role != "admin" and agent.get("owner") != username:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Kein Zugriff")
    return agent


@router.post("", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_specialist(req: CreateSpecialistRequest) -> dict:
    return agent_config.create(
        agent_type="specialist",
        name=req.name,
        llm_model=req.llm_model,
        tools=req.tools if req.tools else agent_config.DEFAULT_TOOLS["specialist"],
        execution_mode=req.execution_mode,
        domain=req.domain,
    )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_agent(agent_id: str) -> None:
    if not agent_config.delete(agent_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent nicht gefunden")
