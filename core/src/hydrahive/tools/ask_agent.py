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

from hydrahive.agentlink.runtime_profiles import OVERRUN_PROFILE, reason_with_profile, thread_key
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
from hydrahive.tools import _ask_agent_background as _bg
from hydrahive.tools._ask_agent_prepare import build_briefing, map_context, missing_briefing, project_refusal
from hydrahive.tools._ask_agent_schema import DESCRIPTION as _DESCRIPTION, SCHEMA as _SCHEMA
from hydrahive.tools._ask_agent_target import resolve_target
from hydrahive.tools._ask_agent_helpers import (
    caller_agentlink_id as _caller_agentlink_id,
    response_timeout as _response_timeout,
    result_from_response as _result_from_response,
)
from hydrahive.tools.base import Tool, ToolContext, ToolResult
from hydrahive.tools._errors import describe

logger = logging.getLogger(__name__)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    if args.get("cancel"):
        return _bg.cancel_own(ctx, str(args["cancel"]))
    target = (args.get("agent_id") or "").strip()
    task = (args.get("task") or "").strip()
    if not target:
        return ToolResult.fail("agent_id fehlt")
    if not task:
        return ToolResult.fail("task fehlt")
    missing = missing_briefing(args)
    if missing:
        return ToolResult.fail(
            f"Briefing unvollständig, es fehlt: {', '.join(missing)}. goal = was am Ende erreicht sein soll, "
            "deliverable = was zurückkommen soll (z. B. Ursache mit Datei:Zeile). Optional: known, files.")

    # Federation-Routing: "persona@workstation" → remote /remote/chat
    if "@" in target:
        return await _execute_federated(target, task, args, ctx)

    if not settings.agentlink_url:
        return ToolResult.fail(
            "AgentLink ist nicht konfiguriert (HH_AGENTLINK_URL leer). "
            "Tool ist aktuell nicht nutzbar."
        )

    task_type = args.get("task_type") or "feature"
    profile = args.get("profile") or "standard"
    overrun_reason = (args.get("overrun_reason") or "").strip()
    if args.get("overrun"):
        if len(overrun_reason) < 10:
            return ToolResult.fail("overrun braucht overrun_reason (mindestens 10 Zeichen): warum mehr Budget nötig ist")
        profile = OVERRUN_PROFILE
    resume_token = args.get("resume_token")
    raw_context = args.get("context") or {}
    required_skills = args.get("required_skills") or []

    # Nur Agenten, die der Besitzer des Laufs nutzen darf (Task 26841785).
    # Danach auf UUID normalisieren, damit der Projekt-Check UUIDs vergleicht.
    resolution = resolve_target(target, ctx.user_id)
    if resolution.error:
        return ToolResult.fail(resolution.error)
    target_agent = resolution.agent
    _is_internal = target_agent is not None
    if _is_internal:
        target = target_agent["id"]

    refused = project_refusal(ctx.agent_id, target)
    if refused:
        return ToolResult.fail(refused)
    task_description, files, errors = map_context(task, raw_context)
    if not args.get("resume_token"):
        task_description = build_briefing(task_description, args)
    files += [{"path": str(p)} for p in (args.get("files") or [])[:50]]

    background = _bg.wants_background(args, ctx, _is_internal)
    if background:
        refused = _bg.refuse_reason(ctx)
        if refused:
            return ToolResult.fail(refused)

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
                # Plan E6 T4: Folgeaufträge aus derselben Sitzung setzen die Sitzung des Spezialisten fort
                thread=thread_key(ctx.session_id) if ctx.session_id and not resume_token else None,
            )
        except ValueError as exc:
            return ToolResult.fail(str(exc))

    state = State(
        agent_id=caller_al_id,
        task=TaskBlock(type=task_type, description=task_description, status="in_progress"),
        context=ContextBlock(
            files=files,
            git=raw_context.get("git"),
            errors=errors + ([f"Budget-Überschreitung angefordert: {overrun_reason[:500]}"]
                             if profile == OVERRUN_PROFILE else []),
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
        return ToolResult.fail(f"AgentLink-Post fehlgeschlagen: {describe(e)}")

    if not sent.id:
        return ToolResult.fail("AgentLink lieferte keinen state.id zurück")

    # Nur ein Antwort-State vom beauftragten Ziel darf die Future lösen (#184).
    fut = register_pending(sent.id, routing_target)
    wait_timeout = _response_timeout(target_agent, profile)
    if background:
        return _bg.start_or_fail(
            ctx=ctx, state_id=sent.id, target=target_agent, task=task,
            timeout_seconds=wait_timeout, fut=fut, cancel=cancel_pending,
        )
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


async def _execute_federated(target: str, task: str, args: dict, ctx: ToolContext) -> ToolResult:
    """'<agent>@<server>': gekoppelter HydraHive-Server oder A2A-Workstation."""
    from hydrahive.tools._ask_agent_federated import execute_federated
    return await execute_federated(target, task, args, ctx)

TOOL = Tool(name="ask_agent", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="agents")
