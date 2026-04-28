"""First-run / per-user setup helpers."""
from __future__ import annotations

import logging

from hydrahive.agents import _validation, config

logger = logging.getLogger(__name__)


def ensure_master(username: str, llm_model: str = "claude-sonnet-4-6") -> dict:
    """Create a master agent for `username` if none exists yet.

    Silently skips if no LLM is configured yet (first-run before user adds keys).
    """
    existing = [a for a in config.list_by_owner(username) if a.get("type") == "master"]
    if existing:
        return existing[0]
    try:
        return config.create(
            agent_type="master",
            name=f"{username}'s Assistant",
            llm_model=llm_model,
            owner=username,
            created_by=username,
        )
    except _validation.AgentValidationError as e:
        logger.warning(
            "Master-Agent für '%s' nicht angelegt (LLM noch nicht konfiguriert): %s",
            username, e,
        )
        return {}
