"""Skill route schemas + shared helpers."""
from __future__ import annotations

from fastapi import status
from pydantic import BaseModel, Field

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.errors import coded
from hydrahive.skills.models import Skill, SkillSource


class SkillSourceBody(BaseModel):
    url: str
    auth: str = ""
    description: str = ""


class SkillBody(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str = ""
    when_to_use: str = ""
    tools_required: list[str] = []
    sources: list[SkillSourceBody] = []
    body: str = ""


def serialize_skill(s: Skill) -> dict:
    return {
        "name": s.name, "description": s.description, "when_to_use": s.when_to_use,
        "tools_required": list(s.tools_required),
        "sources": [{"url": x.url, "auth": x.auth, "description": x.description} for x in s.sources],
        "body": s.body, "scope": s.scope, "owner": s.owner,
    }


def check_agent_access(agent_id: str, username: str, role: str) -> dict:
    agent = agent_config.get(agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    if role != "admin" and agent.get("owner") != username:
        raise coded(status.HTTP_403_FORBIDDEN, "agent_no_access")
    return agent
