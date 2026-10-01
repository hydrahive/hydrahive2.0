"""Agent-Läufe für zeitgesteuerte Butler-Aktionen."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from fastapi import HTTPException

from hydrahive import buddy
from hydrahive.agents import config as agent_config
from hydrahive.api.middleware import users
from hydrahive.api.routes._session_access import (
    assert_agent_access,
    assert_project_access,
)
from hydrahive.butler.models import TriggerEvent
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import runner
from hydrahive.runner.events import Error

logger = logging.getLogger(__name__)
_AGENT_ACTIONS = {
    "agent_reply", "agent_reply_with_prefix", "agent_reply_guided", "forward",
}
_AGENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


@dataclass
class ScheduledAgentOutcome:
    session_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _directive_block(instruction: str) -> str:
    return (
        "[BETREIBER-VORGABE FÜR DIESEN GEPLANTEN ABLAUF]\n"
        "Diese Vorgabe stammt aus der vertrauenswürdigen Butler-Konfiguration "
        "und gilt nur für diesen automatischen Lauf:\n\n"
        f"{instruction}\n"
        "[/BETREIBER-VORGABE]"
    )


def _owner_role(owner: str) -> str:
    user = users.get_by_username(owner)
    return str((user or {}).get("role") or "user")


def _target_agent(
    action: dict, owner: str, role: str, flow_id: str, project: dict | None,
) -> str | None:
    requested = str(action.get("reply_via_agent") or "").strip()
    if requested == "master" or not requested:
        target_id = str(buddy.get_or_create_buddy(owner)["agent_id"])
    else:
        target_id = requested
    if not _AGENT_ID_RE.fullmatch(target_id):
        logger.warning(
            "Geplanter Butler-Flow %s/%s verwirft ungültige Agent-ID",
            owner, flow_id,
        )
        return None

    agent = agent_config.get(target_id)
    if not agent:
        logger.warning(
            "Geplanter Butler-Flow %s/%s überspringt unbekannten Agenten %s",
            owner, flow_id, target_id,
        )
        return None
    if agent.get("id") != target_id:
        logger.warning(
            "Geplanter Butler-Flow %s/%s verwirft abweichende Agent-Konfiguration",
            owner, flow_id,
        )
        return None
    if not agent.get("owner"):
        logger.warning(
            "Geplanter Butler-Flow %s/%s verwirft Agent ohne Besitzer",
            owner, flow_id,
        )
        return None
    try:
        assert_agent_access(agent, project, owner, role)
    except HTTPException:
        logger.warning(
            "Geplanter Butler-Flow %s/%s darf fremden Agent %s nicht ausführen "
            "(Projektfreigabe fehlt)",
            owner, flow_id, target_id,
        )
        return None
    return target_id


def _is_agent_action(action: dict) -> bool:
    return bool(action.get("reply_via_agent")) or action.get("subtype") in _AGENT_ACTIONS


def _authorized_project(
    project_id: str | None, owner: str, role: str, flow_id: str,
) -> tuple[dict | None, str | None]:
    if not project_id:
        return None, None
    try:
        return assert_project_access(project_id, owner, role), None
    except HTTPException:
        message = f"Projektzugriff für {project_id} nicht mehr erlaubt"
        logger.warning(
            "Geplanter Butler-Flow %s/%s startet nicht: %s",
            owner, flow_id, message,
        )
        return None, message


async def run_scheduled_agent_actions(
    *, owner: str, flow_id: str, flow_name: str, project_id: str | None,
    event: TriggerEvent, actions: list[dict],
) -> ScheduledAgentOutcome:
    """Wertet Routing-Hinweise aus und startet pro Agent-Aktion eine neue Session."""
    outcome = ScheduledAgentOutcome()
    role = _owner_role(owner)
    project, project_error = _authorized_project(project_id, owner, role, flow_id)
    if project_error:
        outcome.errors.append(project_error)
        return outcome

    schedule_id = event.payload.get("schedule_id") or event.payload.get("task_id")
    fired_at = event.timestamp or "unbekannter Zeit"
    user_text = f"Geplanter Butler-Ablauf ‚{flow_name}‘ ausgelöst um {fired_at}."

    for action in actions:
        if action.get("reply_text"):
            logger.info(
                "Geplanter Butler-Flow %s/%s erzeugte reply_text; ohne Kanal nur im Trace",
                owner, flow_id,
            )
        if not _is_agent_action(action):
            continue
        agent_id = _target_agent(action, owner, role, flow_id, project)
        if not agent_id:
            continue
        session = sessions_db.create(
            agent_id=agent_id,
            user_id=owner,
            project_id=project_id,
            title=f"Automatisch: {flow_name}",
            metadata={"flow_id": flow_id, "schedule_id": schedule_id},
        )
        outcome.session_ids.append(session.id)
        instruction = str(action.get("reply_prefix") or "").strip()
        extra_system = _directive_block(instruction) if instruction else None
        try:
            async for runner_event in runner.run(
                session.id, user_text, extra_system=extra_system,
            ):
                if isinstance(runner_event, Error):
                    outcome.errors.append(runner_event.message)
                    logger.warning(
                        "Agent-Lauf für Butler-Flow %s/%s fehlgeschlagen: %s",
                        owner, flow_id, runner_event.message,
                    )
                    break
        except Exception as exc:
            logger.exception(
                "Agent-Lauf für Butler-Flow %s/%s abgebrochen", owner, flow_id,
            )
            outcome.errors.append(str(exc))
    return outcome
