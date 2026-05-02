from __future__ import annotations

import json
import logging
from typing import Any

from hydrahive.agents._defaults import (
    DEFAULT_COMPACT_MODEL,
    DEFAULT_COMPACT_RESERVE_TOKENS,
    DEFAULT_COMPACT_THRESHOLD_PCT,
    DEFAULT_COMPACT_TOOL_RESULT_LIMIT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_THINKING_BUDGET,
)
from hydrahive.agents._paths import config_path
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


def save_atomic(path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)


def normalize(cfg: dict) -> dict:
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
    cfg.setdefault("disabled_skills", [])
    cfg.setdefault("require_tool_confirm", False)
    cfg.setdefault("is_buddy", False)
    cfg.setdefault("compact_model", DEFAULT_COMPACT_MODEL)
    cfg.setdefault("compact_tool_result_limit", DEFAULT_COMPACT_TOOL_RESULT_LIMIT)
    cfg.setdefault("compact_reserve_tokens", DEFAULT_COMPACT_RESERVE_TOKENS)
    cfg.setdefault("compact_threshold_pct", DEFAULT_COMPACT_THRESHOLD_PCT)
    return cfg


def list_all() -> list[dict]:
    if not settings.agents_dir.exists():
        return []
    out = []
    for d in sorted(settings.agents_dir.iterdir()):
        p = d / "config.json"
        if p.exists():
            try:
                out.append(normalize(json.loads(p.read_text())))
            except json.JSONDecodeError:
                logger.warning("Defekte Agent-Config: %s", p)
    return out


def list_by_owner(owner: str) -> list[dict]:
    return [a for a in list_all() if a.get("owner") == owner]


def get(agent_id: str) -> dict | None:
    path = config_path(agent_id)
    if not path.exists():
        return None
    return normalize(json.loads(path.read_text()))
