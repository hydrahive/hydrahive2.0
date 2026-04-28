from __future__ import annotations

import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

AgentType = Literal["master", "project", "specialist"]

DEFAULT_TOOLS: dict[str, list[str]] = {
    "master": [
        "shell_exec", "file_read", "file_write", "file_patch",
        "file_search", "web_search", "http_request",
        "read_memory", "write_memory", "ask_agent", "send_mail",
    ],
    "project": [
        "file_read", "file_write", "file_patch", "file_search",
        "shell_exec", "git", "read_memory", "write_memory",
    ],
    "specialist": [],
}


def _agent_dir(agent_id: str) -> Path:
    return settings.agents_dir / agent_id


def _cfg_path(agent_id: str) -> Path:
    return _agent_dir(agent_id) / "config.json"


def create(
    agent_type: AgentType,
    name: str,
    llm_model: str,
    tools: list[str] | None = None,
    owner: str | None = None,
    execution_mode: str | None = None,
    domain: str | None = None,
    project_id: str | None = None,
    workspace: str | None = None,
) -> dict:
    agent_id = str(uuid.uuid4())
    cfg: dict = {
        "id": agent_id,
        "type": agent_type,
        "name": name,
        "owner": owner,
        "llm_model": llm_model,
        "tools": tools if tools is not None else DEFAULT_TOOLS[agent_type],
        "execution_mode": execution_mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if domain is not None:
        cfg["domain"] = domain
    if project_id is not None:
        cfg["project_id"] = project_id
    if workspace is not None:
        cfg["workspace"] = workspace

    agent_dir = _agent_dir(agent_id)
    agent_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("soul", "memory", "skills"):
        (agent_dir / sub).mkdir(exist_ok=True)
    _cfg_path(agent_id).write_text(json.dumps(cfg, indent=2))
    logger.info("Agent '%s' angelegt (type=%s, owner=%s)", name, agent_type, owner)
    return cfg


def get(agent_id: str) -> dict | None:
    path = _cfg_path(agent_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def list_all() -> list[dict]:
    if not settings.agents_dir.exists():
        return []
    result = []
    for d in settings.agents_dir.iterdir():
        p = d / "config.json"
        if p.exists():
            result.append(json.loads(p.read_text()))
    return result


def list_by_owner(owner: str) -> list[dict]:
    return [a for a in list_all() if a.get("owner") == owner]


def ensure_master(username: str, llm_model: str = "claude-sonnet-4-6") -> dict:
    """Creates a Masteragent for username if none exists yet."""
    existing = [a for a in list_by_owner(username) if a["type"] == "master"]
    if existing:
        return existing[0]
    return create(
        agent_type="master",
        name=f"{username}'s Assistant",
        llm_model=llm_model,
        owner=username,
    )


def delete(agent_id: str) -> bool:
    d = _agent_dir(agent_id)
    if not d.exists():
        return False
    shutil.rmtree(d)
    return True
