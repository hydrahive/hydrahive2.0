"""First-run / per-user setup helpers."""
from __future__ import annotations

import logging
from pathlib import Path

from hydrahive.agents import _validation, config
from hydrahive.agents._defaults import _BASE_TOOLS
from hydrahive.agents._paths import ensure_workspace

logger = logging.getLogger(__name__)

_STARTUP_TEMPLATE = Path(__file__).parent / "_startup_template.md"


def _write_startup(agent: dict) -> None:
    """Write startup.md into the agent's workspace — only if not already there."""
    if not _STARTUP_TEMPLATE.exists():
        return
    ws = ensure_workspace(agent)
    startup = ws / "startup.md"
    if startup.exists():
        return
    startup.write_text(_STARTUP_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")


def migrate_tools() -> None:
    """Stellt sicher dass alle bestehenden Agenten die Tools aus _BASE_TOOLS haben.

    Läuft bei jedem Start — idempotent. Neue Tools in _BASE_TOOLS werden so
    automatisch in bestehende Agent-Configs übernommen ohne manuellen Eingriff.

    Nutzt direktes save_atomic statt config.update, damit Agenten mit Plugin-Tools
    (plugin__*) nicht an der Validation scheitern — wir fügen nur hinzu, nie entfernen.
    """
    from hydrahive.agents._config_utils import list_all, save_atomic
    from hydrahive.agents._paths import config_path
    from hydrahive.db._utils import now_iso
    for agent in list_all():
        agent_type = agent.get("type", "")
        if agent_type not in _BASE_TOOLS:
            continue
        current: list[str] = agent.get("tools", [])
        canonical: list[str] = _BASE_TOOLS[agent_type]
        missing = [t for t in canonical if t not in current]
        if not missing:
            continue
        try:
            agent["tools"] = current + missing
            agent["updated_at"] = now_iso()
            save_atomic(config_path(agent["id"]), agent)
            logger.info(
                "Agent '%s' (%s): Tools ergänzt: %s",
                agent.get("name"), agent["id"], missing,
            )
        except Exception as e:
            logger.warning("Tool-Migration für Agent %s fehlgeschlagen: %s", agent["id"], e)


def ensure_master(username: str, llm_model: str = "claude-sonnet-4-6") -> dict:
    """Create a master agent for `username` if none exists yet.

    Silently skips if no LLM is configured yet (first-run before user adds keys).
    """
    existing = [a for a in config.list_by_owner(username) if a.get("type") == "master"]
    if existing:
        return existing[0]
    try:
        agent = config.create(
            agent_type="master",
            name=f"{username}'s Assistant",
            llm_model=llm_model,
            owner=username,
            created_by=username,
            temperature=1.0,
            max_tokens=16000,
            thinking_budget=0,
        )
        _write_startup(agent)
        from hydrahive.agents._workspace_links import sync_links_for_user
        sync_links_for_user(username)
        return agent
    except _validation.AgentValidationError as e:
        logger.warning(
            "Master-Agent für '%s' nicht angelegt (LLM noch nicht konfiguriert): %s",
            username, e,
        )
        return {}
