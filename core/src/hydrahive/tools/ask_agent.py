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

from hydrahive.agentlink.runtime_profiles import reason_with_profile
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
from hydrahive.tools._ask_agent_helpers import (
    caller_agentlink_id as _caller_agentlink_id,
    response_timeout as _response_timeout,
    result_from_response as _result_from_response,
)
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
        "agent_id": {
            "type": "string",
            "description": (
                "ID oder Name des Ziel-Agenten. "
                "Für Federation-Workstations: 'persona@workstation-name', z.B. 'geralt@projektx-till'."
            ),
        },
        "task": {"type": "string", "description": "Aufgabenbeschreibung für den Ziel-Agenten."},
        "task_type": {
            "type": "string",
            "description": "Task-Typ. Default 'feature'.",
            "enum": ["bug_fix", "feature", "review", "research", "refactor"],
        },
        "context": {
            "type": "object",
            "description": (
                "Optionale Zusatz-Daten für den Ziel-Agenten. Unterstützte Keys: "
                "error_log (str), code_snippet (str), related_files (list[str]), "
                "files (list[dict]), errors (list[str]), git (dict)."
            ),
            "properties": {
                "error_log":      {"type": "string"},
                "code_snippet":   {"type": "string"},
                "related_files":  {"type": "array", "items": {"type": "string"}},
                "files":          {"type": "array",  "items": {"type": "object"}},
                "errors":         {"type": "array",  "items": {"type": "string"}},
                "git":            {"type": "object"},
            },
        },
        "profile": {
            "type": "string",
            "enum": ["quick", "standard", "deep"],
            "description": "Runtime-Profil für interne Spezialisten. Default: standard.",
        },
        "resume_token": {
            "type": "string",
            "pattern": "^[A-Za-z0-9_-]{8,128}$",
            "description": "Einmal-Token aus einem pausierten Spezialistenlauf.",
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
    target = (args.get("agent_id") or "").strip()
    task = (args.get("task") or "").strip()
    if not target:
        return ToolResult.fail("agent_id fehlt")
    if not task:
        return ToolResult.fail("task fehlt")

    # Federation-Routing: "persona@workstation" → remote /remote/chat
    if "@" in target:
        return await _execute_federated(target, task, args)

    if not settings.agentlink_url:
        return ToolResult.fail(
            "AgentLink ist nicht konfiguriert (HH_AGENTLINK_URL leer). "
            "Tool ist aktuell nicht nutzbar."
        )

    task_type = args.get("task_type") or "feature"
    profile = args.get("profile") or "standard"
    resume_token = args.get("resume_token")
    raw_context = args.get("context") or {}
    required_skills = args.get("required_skills") or []

    # UUID-Normalisierung zuerst: Name → UUID, damit der Auth-Check UUIDs vergleicht
    target_agent: dict | None = None
    try:
        from hydrahive.agents import config as _ac
        all_agents = _ac.list_all()
        target_agent = (
            _ac.get(target)
            or next((a for a in all_agents if a.get("name", "").lower() == target.lower()), None)
            or next((a for a in all_agents if target.lower() in a.get("name", "").lower()), None)
        )
        _is_internal = bool(target_agent)
        if _is_internal:
            target = target_agent["id"]  # auf UUID normalisieren
    except Exception:
        _is_internal = False

    # Project-Agents dürfen nur freigegebene Specialists beauftragen (nach UUID-Normalisierung)
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

    # Friendly-Key-Mapping: error_log / code_snippet / related_files
    errors = list(raw_context.get("errors") or [])
    if raw_context.get("error_log"):
        errors.append(raw_context["error_log"])

    files = list(raw_context.get("files") or [])
    for p in raw_context.get("related_files") or []:
        files.append({"path": str(p)})

    task_description = task
    if raw_context.get("code_snippet"):
        task_description = f"{task}\n\n```\n{raw_context['code_snippet']}\n```"

    # Security identity must be stable across renames and unique even when two
    # agents share the same display name. UI names stay in local config/logs.
    caller_al_id = _caller_agentlink_id(ctx.agent_id)

    routing_target = settings.agentlink_agent_id if _is_internal else target
    task_reason = f"hh-task: {task[:120]}"
    if resume_token and not _is_internal:
        return ToolResult.fail("Resume-Tokens werden nur für interne Spezialisten unterstützt")
    if _is_internal:
        try:
            task_reason = reason_with_profile(
                target, profile, task[:120], resume_token=resume_token,
            )
        except ValueError as exc:
            return ToolResult.fail(str(exc))

    state = State(
        agent_id=caller_al_id,
        task=TaskBlock(type=task_type, description=task_description, status="in_progress"),
        context=ContextBlock(
            files=files,
            git=raw_context.get("git"),
            errors=errors,
        ),
        handoff=Handoff(
            to_agent=routing_target,
            reason=task_reason,
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

    # Nur ein Antwort-State vom beauftragten Ziel darf die Future lösen (#184).
    fut = register_pending(sent.id, routing_target)
    wait_timeout = _response_timeout(target_agent, profile)
    try:
        response = await asyncio.wait_for(fut, timeout=wait_timeout)
    except asyncio.TimeoutError:
        cancel_pending(sent.id)
        return ToolResult.fail(
            f"Timeout nach {wait_timeout}s — '{target}' hat nicht "
            f"geantwortet. State-ID: {sent.id}"
        )
    except asyncio.CancelledError:
        cancel_pending(sent.id)
        raise

    return _result_from_response(response)


async def _execute_federated(target: str, task: str, args: dict) -> ToolResult:
    """Routing für 'persona@workstation' — sendet via /remote/chat."""
    persona_id, _, ws_name = target.partition("@")
    persona_id = persona_id.strip()
    ws_name = ws_name.strip()

    try:
        from hydrahive.db import federation as fed_db
        from hydrahive.federation.registry import remote_chat

        # Workstation by name, ID, or URL-prefix
        ws = (
            fed_db.get_by_name(ws_name)
            or fed_db.get_workstation(ws_name)
        )
        if not ws:
            return ToolResult.fail(
                f"Federation-Workstation '{ws_name}' nicht gefunden. "
                "Bitte zuerst im Federation-Panel registrieren."
            )
        if not ws.get("enabled"):
            return ToolResult.fail(f"Workstation '{ws['name']}' ist deaktiviert.")

        result = await remote_chat(ws["id"], task, persona_id=persona_id)
        label = f"{persona_id}@{ws['name']}" if persona_id else ws["name"]
        return ToolResult.ok(f"[{label}]: {result}")
    except Exception as e:
        logger.exception("Federation remote_chat fehlgeschlagen: %s", e)
        return ToolResult.fail(f"Federation-Fehler: {e}")


TOOL = Tool(name="ask_agent", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="agents")
