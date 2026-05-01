from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, Field

from hydrahive.agents import AgentValidationError, config as agent_config
from hydrahive.agents._defaults import DEFAULT_TOOLS
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.plugins import tool_bridge as plugin_bridge
from hydrahive.tools import REGISTRY as TOOL_REGISTRY

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentCreate(BaseModel):
    type: str
    name: str
    llm_model: str
    tools: list[str] | None = None
    owner: str | None = None
    description: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    thinking_budget: int = 0
    mcp_servers: list[str] = []
    fallback_models: list[str] = []
    project_id: str | None = None
    domain: str | None = None
    system_prompt: str | None = None
    # Per-Agent Compaction-Settings (#82)
    compact_model: str | None = None
    compact_tool_result_limit: int | None = None
    compact_reserve_tokens: int | None = None
    compact_threshold_pct: int | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    llm_model: str | None = None
    tools: list[str] | None = None
    owner: str | None = None
    description: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    thinking_budget: int | None = None
    mcp_servers: list[str] | None = None
    fallback_models: list[str] | None = None
    domain: str | None = None
    status: str | None = None
    # Per-Agent Compaction-Settings (#82)
    compact_model: str | None = None
    compact_tool_result_limit: int | None = None
    compact_reserve_tokens: int | None = None
    compact_threshold_pct: int | None = None


class SystemPromptUpdate(BaseModel):
    prompt: str = Field(..., min_length=1)


def _check_access(agent: dict, username: str, role: str) -> None:
    if role != "admin" and agent.get("owner") != username:
        raise coded(status.HTTP_403_FORBIDDEN, "agent_no_access")


@router.get("/_meta/tools")
def list_available_tools(_: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    core = [
        {"name": t.name, "description": t.description, "category": t.category}
        for t in TOOL_REGISTRY.values()
    ]
    return core + plugin_bridge.all_tool_meta()


@router.get("/_meta/defaults")
def list_defaults(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    # dict(DEFAULT_TOOLS) entpackt den LazyDefaultTools-Wrapper für die
    # JSON-Serialisierung (siehe agents/_defaults.py).
    return {"tools_per_type": dict(DEFAULT_TOOLS), "types": list(DEFAULT_TOOLS.keys())}


@router.get("")
def list_agents(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    username, role = auth
    if role == "admin":
        return agent_config.list_all()
    return agent_config.list_by_owner(username)


@router.get("/{agent_id}")
def get_agent(
    agent_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    agent = agent_config.get(agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    _check_access(agent, *auth)
    from hydrahive.agents._paths import workspace_for
    return {**agent, "workspace": str(workspace_for(agent))}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_agent(
    req: AgentCreate,
    auth: Annotated[tuple[str, str], Depends(require_admin)],
) -> dict:
    creator, _ = auth
    try:
        return agent_config.create(
            agent_type=req.type,
            name=req.name,
            llm_model=req.llm_model,
            tools=req.tools,
            owner=req.owner or creator,
            created_by=creator,
            description=req.description,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            thinking_budget=req.thinking_budget,
            mcp_servers=req.mcp_servers,
            fallback_models=req.fallback_models,
            project_id=req.project_id,
            domain=req.domain,
            system_prompt=req.system_prompt,
        )
    except AgentValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))


@router.patch("/{agent_id}", dependencies=[Depends(require_admin)])
def update_agent(agent_id: str, req: AgentUpdate) -> dict:
    changes = {k: v for k, v in req.model_dump().items() if v is not None}
    if not changes:
        agent = agent_config.get(agent_id)
        if not agent:
            raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
        return agent
    try:
        return agent_config.update(agent_id, **changes)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    except AgentValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_agent(agent_id: str) -> None:
    if not agent_config.delete(agent_id):
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")


@router.get("/{agent_id}/system_prompt")
def get_system_prompt(
    agent_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    agent = agent_config.get(agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    _check_access(agent, *auth)
    return {"prompt": agent_config.get_system_prompt(agent_id)}


@router.put("/{agent_id}/system_prompt", dependencies=[Depends(require_admin)])
def set_system_prompt(agent_id: str, req: SystemPromptUpdate) -> dict:
    try:
        agent_config.set_system_prompt(agent_id, req.prompt)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    return {"prompt": req.prompt}
