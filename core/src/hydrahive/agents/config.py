from __future__ import annotations

import logging
import shutil
import uuid
from typing import Any

from hydrahive.agents import _prompt, _tool_config, _validation
from hydrahive.agents._config_utils import (
    get, list_all, list_by_owner, normalize, save_atomic,
)
from hydrahive.agents._defaults import (
    DEFAULT_HANDOFF_TIMEOUT_SECONDS,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_SPECIALIST_MAX_ITERATIONS,
    DEFAULT_TOOLS,
)
from hydrahive.agents._paths import agent_dir, config_path, ensure_workspace
from hydrahive.db._utils import now_iso

logger = logging.getLogger(__name__)

AgentType = str


def create(
    agent_type: AgentType,
    name: str,
    llm_model: str,
    *,
    tools: list[str] | None = None,
    owner: str | None = None,
    created_by: str | None = None,
    description: str = "",
    temperature: float,
    max_tokens: int,
    thinking_budget: int,
    reasoning_effort: str = "",
    mcp_servers: list[str] | None = None,
    fallback_models: list[str] | None = None,
    project_id: str | None = None,
    domain: str | None = None,
    system_prompt: str | None = None,
    external: bool = False,
    compact_model: str | None = None,
    compact_tool_result_limit: int | None = None,
    compact_reserve_tokens: int | None = None,
    compact_threshold_pct: int | None = None,
    compact_max_turns: int | None = None,
    max_iterations: int | None = None,
    tool_result_max_chars: int | None = None,
    cache_ttl: str | None = None,
    handoff_timeout_seconds: int | None = None,
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
        "id": agent_id, "type": agent_type, "name": name,
        "owner": owner, "created_by": created_by or owner,
        "llm_model": llm_model, "fallback_models": list(fallback_models or []),
        "tools": list(tools), "mcp_servers": list(mcp_servers or []),
        "description": description, "temperature": float(temperature),
        "max_tokens": int(max_tokens), "thinking_budget": int(thinking_budget),
        "reasoning_effort": reasoning_effort,
        "status": "active", "created_at": now_iso(), "updated_at": now_iso(),
        "external": bool(external),
    }
    runtime = {
        key: value for key, value in {
            "compact_model": compact_model,
            "compact_tool_result_limit": compact_tool_result_limit,
            "compact_reserve_tokens": compact_reserve_tokens,
            "compact_threshold_pct": compact_threshold_pct,
            "compact_max_turns": compact_max_turns,
            "max_iterations": max_iterations,
            "tool_result_max_chars": tool_result_max_chars,
            "cache_ttl": cache_ttl,
            "handoff_timeout_seconds": handoff_timeout_seconds,
        }.items() if value is not None
    }
    runtime["max_iterations"] = (
        max_iterations if max_iterations is not None
        else DEFAULT_SPECIALIST_MAX_ITERATIONS
        if agent_type == "specialist" else DEFAULT_MAX_ITERATIONS
    )
    runtime["handoff_timeout_seconds"] = (
        handoff_timeout_seconds
        if handoff_timeout_seconds is not None else DEFAULT_HANDOFF_TIMEOUT_SECONDS
    )
    _validation.normalize_compact_changes(runtime)
    cfg.update(runtime)
    if project_id:
        cfg["project_id"] = project_id
    if domain:
        cfg["domain"] = domain

    agent_dir(agent_id).mkdir(parents=True, exist_ok=True)
    save_atomic(config_path(agent_id), cfg)
    if system_prompt:
        _prompt.save(agent_id, system_prompt)
    else:
        _prompt.init_default(agent_id, agent_type)
    ensure_workspace(cfg)

    logger.info("Agent '%s' angelegt (id=%s, type=%s)", name, agent_id, agent_type)
    return cfg


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
    if "tool_config" in changes:
        # Erst mergen (strippt das API-Masking-Flag `password_set` + behält
        # leere Passwörter), DANN validieren — sonst würde das vom Frontend
        # zurückgeschickte `password_set` als unbekannter Key abgelehnt.
        merged = _tool_config.merge_secrets(cfg.get("tool_config"), changes["tool_config"])
        _validation.validate_tool_config(merged)
        changes["tool_config"] = merged

    clear_fields = {
        field
        for field in ("compact_max_turns",)
        if field in changes and changes[field] in (None, "")
    }
    _validation.normalize_compact_changes(changes)

    for field in clear_fields:
        cfg.pop(field, None)
    cfg.update(changes)
    cfg["updated_at"] = now_iso()
    save_atomic(config_path(agent_id), cfg)
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
    save_atomic(config_path(agent_id), cfg)


def delete(agent_id: str) -> bool:
    d = agent_dir(agent_id)
    if not d.exists():
        return False
    shutil.rmtree(d)
    logger.info("Agent gelöscht: %s", agent_id)
    return True
