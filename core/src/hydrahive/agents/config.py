from __future__ import annotations

import json
import logging
import shutil
import uuid
from typing import Any, Literal

from hydrahive.agents import _prompt, _validation
from hydrahive.agents._defaults import (
    DEFAULT_COMPACT_MODEL,
    DEFAULT_COMPACT_RESERVE_TOKENS,
    DEFAULT_COMPACT_THRESHOLD_PCT,
    DEFAULT_COMPACT_TOOL_RESULT_LIMIT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_THINKING_BUDGET,
    DEFAULT_TOOLS,
)
from hydrahive.agents._paths import agent_dir, config_path, ensure_workspace
from hydrahive.db._utils import now_iso
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

AgentType = Literal["master", "project", "specialist"]


def _save_atomic(path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)


def create(
    agent_type: AgentType,
    name: str,
    llm_model: str,
    *,
    tools: list[str] | None = None,
    owner: str | None = None,
    created_by: str | None = None,
    description: str = "",
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    thinking_budget: int = DEFAULT_THINKING_BUDGET,
    mcp_servers: list[str] | None = None,
    fallback_models: list[str] | None = None,
    project_id: str | None = None,
    domain: str | None = None,
    system_prompt: str | None = None,
) -> dict:
    _validation.validate_type(agent_type)
    _validation.validate_model(llm_model)
    if tools is None:
        tools = DEFAULT_TOOLS[agent_type]
    _validation.validate_tools(tools)
    _validation.validate_temperature(temperature)
    _validation.validate_max_tokens(max_tokens)
    if fallback_models:
        _validation.validate_fallback_models(fallback_models)

    agent_id = str(uuid.uuid4())
    cfg: dict[str, Any] = {
        "id": agent_id,
        "type": agent_type,
        "name": name,
        "owner": owner,
        "created_by": created_by or owner,
        "llm_model": llm_model,
        "fallback_models": list(fallback_models or []),
        "tools": list(tools),
        "mcp_servers": list(mcp_servers or []),
        "description": description,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
        "thinking_budget": int(thinking_budget),
        "status": "active",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    if project_id:
        cfg["project_id"] = project_id
    if domain:
        cfg["domain"] = domain

    agent_dir(agent_id).mkdir(parents=True, exist_ok=True)
    _save_atomic(config_path(agent_id), cfg)
    if system_prompt:
        _prompt.save(agent_id, system_prompt)
    else:
        _prompt.init_default(agent_id, agent_type)
    ensure_workspace(cfg)

    logger.info("Agent '%s' angelegt (id=%s, type=%s)", name, agent_id, agent_type)
    return cfg


def _normalize(cfg: dict) -> dict:
    """Backfill defaults for fields that may be missing in older configs."""
    cfg.setdefault("status", "active")
    cfg.setdefault("description", "")
    cfg.setdefault("temperature", DEFAULT_TEMPERATURE)
    cfg.setdefault("max_tokens", DEFAULT_MAX_TOKENS)
    cfg.setdefault("thinking_budget", DEFAULT_THINKING_BUDGET)
    cfg.setdefault("mcp_servers", [])
    cfg.setdefault("fallback_models", [])
    cfg.setdefault("updated_at", cfg.get("created_at", ""))
    cfg.setdefault("created_by", cfg.get("owner"))
    cfg.setdefault("tools", [])
    cfg.setdefault("compact_model", DEFAULT_COMPACT_MODEL)
    cfg.setdefault("compact_tool_result_limit", DEFAULT_COMPACT_TOOL_RESULT_LIMIT)
    cfg.setdefault("compact_reserve_tokens", DEFAULT_COMPACT_RESERVE_TOKENS)
    cfg.setdefault("compact_threshold_pct", DEFAULT_COMPACT_THRESHOLD_PCT)
    return cfg


def get(agent_id: str) -> dict | None:
    path = config_path(agent_id)
    if not path.exists():
        return None
    return _normalize(json.loads(path.read_text()))


def list_all() -> list[dict]:
    if not settings.agents_dir.exists():
        return []
    out = []
    for d in sorted(settings.agents_dir.iterdir()):
        p = d / "config.json"
        if p.exists():
            try:
                out.append(_normalize(json.loads(p.read_text())))
            except json.JSONDecodeError:
                logger.warning("Defekte Agent-Config: %s", p)
    return out


def list_by_owner(owner: str) -> list[dict]:
    return [a for a in list_all() if a.get("owner") == owner]


def update(agent_id: str, **changes: Any) -> dict:
    cfg = get(agent_id)
    if not cfg:
        raise KeyError(f"Agent '{agent_id}' nicht gefunden")

    for protected in ("id", "type", "created_at", "created_by"):
        changes.pop(protected, None)

    if "tools" in changes:
        _validation.validate_tools(changes["tools"])
    if "llm_model" in changes:
        _validation.validate_model(changes["llm_model"])
    if "fallback_models" in changes:
        _validation.validate_fallback_models(changes["fallback_models"])
    if "temperature" in changes:
        _validation.validate_temperature(changes["temperature"])
    if "max_tokens" in changes:
        _validation.validate_max_tokens(changes["max_tokens"])
    if "status" in changes:
        _validation.validate_status(changes["status"])
    if "compact_model" in changes:
        _validation.validate_compact_model(changes["compact_model"])
    if "compact_tool_result_limit" in changes:
        _validation.validate_compact_tool_result_limit(changes["compact_tool_result_limit"])
    if "compact_reserve_tokens" in changes:
        _validation.validate_compact_reserve_tokens(changes["compact_reserve_tokens"])
    if "compact_threshold_pct" in changes:
        _validation.validate_compact_threshold_pct(changes["compact_threshold_pct"])

    cfg.update(changes)
    cfg["updated_at"] = now_iso()
    _save_atomic(config_path(agent_id), cfg)
    return cfg


def get_system_prompt(agent_id: str) -> str:
    cfg = get(agent_id)
    if not cfg:
        raise KeyError(f"Agent '{agent_id}' nicht gefunden")
    return _prompt.load(agent_id, cfg.get("type", "specialist"))


def set_system_prompt(agent_id: str, prompt: str) -> None:
    cfg = get(agent_id)
    if not cfg:
        raise KeyError(f"Agent '{agent_id}' nicht gefunden")
    _prompt.save(agent_id, prompt)
    cfg["updated_at"] = now_iso()
    _save_atomic(config_path(agent_id), cfg)


def delete(agent_id: str) -> bool:
    d = agent_dir(agent_id)
    if not d.exists():
        return False
    shutil.rmtree(d)
    logger.info("Agent gelöscht: %s", agent_id)
    return True
