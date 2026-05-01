from __future__ import annotations

from pathlib import Path

from hydrahive.settings import settings
from hydrahive.skills.models import SkillScope


def system_dir() -> Path:
    return settings.data_dir / "skills" / "system"


def user_dir(username: str) -> Path:
    return settings.data_dir / "users" / username / "skills"


def agent_dir(agent_id: str) -> Path:
    return settings.data_dir / "agents" / agent_id / "skills"


def dir_for(scope: SkillScope, owner: str) -> Path:
    if scope == "system":
        return system_dir()
    if scope == "user":
        return user_dir(owner)
    if scope == "agent":
        return agent_dir(owner)
    raise ValueError(f"unbekannter scope: {scope}")


def file_for(scope: SkillScope, owner: str, name: str) -> Path:
    return dir_for(scope, owner) / f"{name}.md"
