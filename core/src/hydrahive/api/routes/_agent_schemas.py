from __future__ import annotations

from fastapi import status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.errors import coded


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
    compact_model: str | None = None
    compact_tool_result_limit: int | None = None
    compact_reserve_tokens: int | None = None
    compact_threshold_pct: int | None = None
    require_tool_confirm: bool | None = None


class SystemPromptUpdate(BaseModel):
    prompt: str = Field(..., min_length=1)


def check_agent_access(agent: dict, username: str, role: str) -> None:
    if role != "admin" and agent.get("owner") != username:
        raise coded(status.HTTP_403_FORBIDDEN, "agent_no_access")
