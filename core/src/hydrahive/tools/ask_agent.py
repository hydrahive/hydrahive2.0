"""ask_agent — Beauftragt einen anderen Agenten via AgentLink (WebSocket).

Flow:
1. Master postet einen State mit handoff.to_agent = target via REST.
2. Future wird im AgentLink-Client registriert (key = unsere state.id).
3. Ziel-Agent bekommt via Redis-Pub/Sub + WebSocket den Push, arbeitet, postet
   einen Antwort-State zurück mit handoff.reason = \"reply_to:<our_state_id>\".
4. Unser WS-Listener resolved die Future → ask_agent gibt das Resultat als
   Tool-Output zurück.

Timeout: settings.agentlink_handoff_timeout (default 600s = 10 min).
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.agentlink import (
    ContextBlock,
    Handoff,
    State,
    TaskBlock,
    cancel_pending,
    post_state,
    register_pending,
)
from hydrahive.settings import settings
from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)


_DESCRIPTION = (
    "Beauftragt einen anderen Agenten über AgentLink. Schickt einen State mit "
    "Task-Beschreibung an den Ziel-Agenten und wartet auf dessen Antwort-State. "
    "Verwende für Handoffs an Spezialisten oder Project-Agents."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "agent_id": {"type": "string", "description": "ID des Ziel-Agenten."},
        "task": {"type": "string", "description": "Aufgabenbeschreibung für den Ziel-Agenten."},
        "task_type": {
            "type": "string",
            "description": "Task-Typ. Default 'feature'.",
            "enum": ["bug_fix", "feature", "review", "research", "refactor"],
        },
        "context": {
            "type": "object",
            "description": "Optionale Zusatz-Daten (files, git, errors).",
        },
        "required_skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optionale Skill-Liste die der Ziel-Agent haben muss.",
        },
    },
    "required": ["agent_id", "task"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    if not settings.agentlink_url:
        return ToolResult.fail(
            "AgentLink ist nicht konfiguriert (HH_AGENTLINK_URL leer). "
            "Tool ist aktuell nicht nutzbar."
        )

    target = (args.get("agent_id") or "").strip()
    task = (args.get("task") or "").strip()
    if not target:
        return ToolResult.fail("agent_id fehlt")
    if not task:
        return ToolResult.fail("task fehlt")

    # Project-Agents dürfen nur freigegebene Specialists beauftragen
    try:
        from hydrahive.agents import config as agent_config
        from hydrahive.projects import config as project_config
        calling = agent_config.get(ctx.agent_id)
        if calling and calling.get("type") == "project":
            project_id = calling.get("project_id")
            if project_id:
                proj = project_config.get(project_id)
                allowed = proj.get("allowed_specialists", []) if proj else []
                if allowed and target not in allowed:
                    return ToolResult.fail(
                        f"Specialist '{target}' ist für dieses Projekt nicht freigegeben. "
                        f"Freigegeben: {allowed}"
                    )
    except Exception as e:
        logger.debug("Specialists-Check übersprungen: %s", e)

    task_type = args.get("task_type") or "feature"
    raw_context = args.get("context") or {}
    required_skills = args.get("required_skills") or []

    state = State(
        agent_id=settings.agentlink_agent_id,
        task=TaskBlock(type=task_type, description=task, status="in_progress"),
        context=ContextBlock(
            files=raw_context.get("files", []),
            git=raw_context.get("git"),
            errors=raw_context.get("errors", []),
        ),
        handoff=Handoff(
            to_agent=target,
            reason=f"hh-task: {task[:120]}",
            required_skills=required_skills,
        ),
    )

    try:
        sent = await post_state(state)
    except Exception as e:
        logger.exception("AgentLink post_state fehlgeschlagen")
        return ToolResult.fail(f"AgentLink-Post fehlgeschlagen: {type(e).__name__}: {e}")

    if not sent.id:
        return ToolResult.fail("AgentLink lieferte keinen state.id zurück")

    fut = register_pending(sent.id)
    try:
        response = await asyncio.wait_for(fut, timeout=settings.agentlink_handoff_timeout)
    except asyncio.TimeoutError:
        cancel_pending(sent.id)
        return ToolResult.fail(
            f"Timeout nach {settings.agentlink_handoff_timeout}s — '{target}' hat nicht "
            f"geantwortet. State-ID: {sent.id}"
        )
    except asyncio.CancelledError:
        cancel_pending(sent.id)
        raise

    # Antwort-State auswerten — Inhalt in working_memory.findings + task.description
    findings = response.working_memory.findings if response.working_memory else []
    description = response.task.description if response.task else ""
    summary_parts: list[str] = []
    if description:
        summary_parts.append(description)
    for f in findings:
        what = f.get("what") if isinstance(f, dict) else None
        if what:
            summary_parts.append(f"- {what}")
    output = "\n".join(summary_parts) if summary_parts else \
        f"Antwort-State {response.id} ohne lesbaren Inhalt."

    return ToolResult.ok(output)


TOOL = Tool(name="ask_agent", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="agents")
