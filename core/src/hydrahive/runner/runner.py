from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from hydrahive.agents import config as agent_config
from hydrahive.agents._paths import ensure_workspace
from hydrahive.compaction import compact_session, should_compact
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.mcp import tool_bridge as mcp_bridge
from hydrahive.plugins import tool_bridge as plugin_bridge
from hydrahive.runner._call import CallResult, call_with_stream_or_fallback
from hydrahive.runner.context import (
    extract_tool_uses,
    heal_orphan_tool_uses,
    to_anthropic_messages,
)
from hydrahive.runner.dispatcher import execute_tool, to_tool_result_block
from hydrahive.runner.events import (
    Done,
    Error,
    Event,
    IterationStart,
    ToolConfirmRequired,
    ToolUseResult,
    ToolUseStart,
)
from hydrahive.runner import tool_confirmation
from hydrahive.tools import ToolContext, schemas_for

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 30
LOOP_DETECTION_WINDOW = 3  # 3× identisches Tool-Use → Abbruch


async def run(
    session_id: str,
    user_input: str | list,
    *,
    tool_config: dict | None = None,
    extra_system: str | None = None,
) -> AsyncIterator[Event]:
    """Run one user turn against the agent. Yields events; persists state.

    Caller is responsible for SSE-encoding the events for HTTP. Errors are
    yielded as Error-events (not raised) so the stream stays well-formed.

    `extra_system` wird als zusätzlicher Kontext-Block VOR dem agent-eigenen
    system_prompt eingefügt (call-spezifisch, nicht persistiert). Aktueller
    Use-Case: WhatsApp-Voice-Mode-Hinweis damit der Master weiß dass das
    Backend TTS automatisch macht — kein eigenmächtiger mmx-Aufruf.
    """
    session = sessions_db.get(session_id)
    if not session:
        yield Error(f"Session '{session_id}' nicht gefunden")
        return

    agent = agent_config.get(session.agent_id)
    if not agent:
        yield Error(f"Agent '{session.agent_id}' nicht gefunden (Session ist verwaist)")
        return
    if agent.get("status") != "active":
        yield Error(f"Agent '{agent['name']}' ist deaktiviert")
        return

    workspace = ensure_workspace(agent)
    ctx = ToolContext(
        session_id=session_id,
        agent_id=agent["id"],
        user_id=session.user_id,
        workspace=workspace,
        config=tool_config or {},
    )

    base_system_prompt = agent_config.get_system_prompt(agent["id"])
    local_tools: list[str] = agent.get("tools", [])
    mcp_servers: list[str] = agent.get("mcp_servers", [])

    # MCP-Tools mergen (lazy connect bei Bedarf, Fehler eines Servers blockt Run nicht)
    mcp_schemas = await mcp_bridge.schemas_for_servers(mcp_servers)
    plugin_schemas = plugin_bridge.schemas_for(local_tools)
    tool_schemas = schemas_for(local_tools) + mcp_schemas + plugin_schemas
    allowed_tools = local_tools + [s["name"] for s in mcp_schemas]

    # Persist user message
    messages_db.append(session_id, "user", user_input)

    last_assistant_id: str | None = None
    recent_tool_calls: list[str] = []  # Loop-Detection-Buffer
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_creation = 0
    total_cache_read = 0

    # Per-Agent Compact-Konfiguration (#82) — alle Felder haben sinnvolle Defaults
    # in agents/_normalize, sind also auch bei alten Agents gesetzt.
    compact_model = agent.get("compact_model") or agent["llm_model"]
    compact_tool_limit = agent.get("compact_tool_result_limit")
    compact_reserve = agent.get("compact_reserve_tokens")
    compact_threshold_pct = int(agent.get("compact_threshold_pct", 100))

    for iteration in range(MAX_ITERATIONS):
        yield IterationStart(iteration=iteration + 1)

        # Build LLM history (resolves through latest compaction)
        history = messages_db.list_for_llm(session_id)
        # Threshold-pct skaliert die Reserve nach oben — niedrigeres pct
        # bedeutet "frühzeitig compactieren". Bei pct=100 entspricht das dem
        # OpenClaw-Verhalten: triggern wenn used > window-reserve.
        effective_reserve = compact_reserve
        if effective_reserve is not None and compact_threshold_pct < 100:
            from hydrahive.compaction.tokens import context_window_for as _cwf
            window = _cwf(agent["llm_model"])
            # equivalent: triggern bei used > window × pct/100
            effective_reserve = max(effective_reserve, window - int(window * compact_threshold_pct / 100))
        should_kwargs = {"reserve_tokens": effective_reserve} if effective_reserve is not None else {}
        if should_compact(history, agent["llm_model"], **should_kwargs):
            try:
                compact_kwargs = {}
                if compact_tool_limit is not None:
                    compact_kwargs["tool_result_limit"] = compact_tool_limit
                await compact_session(session_id, model=compact_model, **compact_kwargs)
                history = messages_db.list_for_llm(session_id)
            except Exception as e:
                logger.warning("Compaction fehlgeschlagen: %s — fahre mit voller History fort", e)

        summary = messages_db.get_latest_summary(session_id)
        system_prompt = (
            f"[Bisherige Zusammenfassung]\n{summary}\n\n{base_system_prompt}"
            if summary else base_system_prompt
        )
        skills_block = _build_skills_block(agent)
        if skills_block:
            system_prompt = f"{system_prompt}\n\n{skills_block}"
        if extra_system:
            system_prompt = f"{extra_system}\n\n{system_prompt}"

        healed_history = heal_orphan_tool_uses(history)
        anth_messages = to_anthropic_messages(healed_history)

        blocks: list[dict] = []
        stop_reason = ""
        iter_input_tokens = 0
        iter_output_tokens = 0
        iter_cache_creation = 0
        iter_cache_read = 0
        used_model = agent["llm_model"]
        try:
            models = [agent["llm_model"]] + list(agent.get("fallback_models", []) or [])
            async for item in call_with_stream_or_fallback(
                models=models,
                system_prompt=system_prompt,
                messages=anth_messages,
                tools=tool_schemas,
                temperature=agent.get("temperature", 0.7),
                max_tokens=agent.get("max_tokens", 4096),
            ):
                if isinstance(item, CallResult):
                    blocks = item.blocks
                    stop_reason = item.stop_reason
                    iter_input_tokens = item.input_tokens
                    iter_output_tokens = item.output_tokens
                    iter_cache_creation = item.cache_creation_tokens
                    iter_cache_read = item.cache_read_tokens
                    used_model = item.model or agent["llm_model"]
                    total_cache_creation += item.cache_creation_tokens
                    total_cache_read += item.cache_read_tokens
                else:
                    yield item
        except Exception as e:
            logger.exception("LLM-Call fehlgeschlagen")
            yield Error(f"LLM-Call fehlgeschlagen: {e}")
            return

        total_input_tokens += iter_input_tokens
        total_output_tokens += iter_output_tokens

        assistant_msg = messages_db.append(
            session_id, "assistant", blocks,
            token_count=iter_output_tokens or None,
            metadata={
                "input_tokens": iter_input_tokens,
                "output_tokens": iter_output_tokens,
                "cache_creation_tokens": iter_cache_creation,
                "cache_read_tokens": iter_cache_read,
                "model": used_model,
                "stop_reason": stop_reason,
                "iteration": iteration + 1,
            },
        )
        last_assistant_id = assistant_msg.id
        history.append(assistant_msg)

        tool_uses = extract_tool_uses(blocks)

        # Truncation-Detection: max_tokens während Tool-Use-Input → JSON kaputt.
        # Wir hängen synthetische tool_results an damit die History valide bleibt
        # (Anthropic verlangt zwingend tool_use/tool_result-Paare).
        if stop_reason == "max_tokens":
            if tool_uses:
                _close_open_tool_uses(session_id, tool_uses, "Abgebrochen: max_tokens-Limit überschritten")
            yield Error(
                f"max_tokens ({agent.get('max_tokens', 4096)}) erreicht — Antwort abgeschnitten. "
                "Tool-Argumente sind unvollständig. Erhöhe max_tokens in der Agent-Config "
                "oder formuliere die Aufgabe so dass weniger Output nötig ist.",
                metadata={"stop_reason": stop_reason, "message_id": assistant_msg.id},
            )
            return

        if not tool_uses:
            yield Done(
                message_id=assistant_msg.id,
                iterations=iteration + 1,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cache_creation_tokens=total_cache_creation,
                cache_read_tokens=total_cache_read,
            )
            return

        # Loop-Detection: identische Tool-Aufrufe in Folge → Abbruch
        signature = "|".join(f"{tu.get('name')}:{json.dumps(tu.get('input', {}), sort_keys=True)}" for tu in tool_uses)
        recent_tool_calls.append(signature)
        recent_tool_calls = recent_tool_calls[-LOOP_DETECTION_WINDOW:]
        if len(recent_tool_calls) == LOOP_DETECTION_WINDOW and len(set(recent_tool_calls)) == 1:
            _close_open_tool_uses(session_id, tool_uses, "Abgebrochen: Loop erkannt, Agent wiederholt sich")
            yield Error(
                f"Loop erkannt — Agent ruft seit {LOOP_DETECTION_WINDOW} Iterationen die exakt gleichen Tools auf. "
                "Stoppe um Tokens zu sparen.",
                metadata={"signature": signature[:200], "message_id": assistant_msg.id},
            )
            return

        result_blocks: list[dict] = []
        require_confirm = bool(agent.get("require_tool_confirm", False))
        for tu in tool_uses:
            tu_id = tu.get("id", "")
            tu_name = tu.get("name", "")
            tu_args = tu.get("input", {}) or {}
            yield ToolUseStart(call_id=tu_id, tool_name=tu_name, arguments=tu_args)

            if require_confirm:
                fut = tool_confirmation.register(tu_id)
                yield ToolConfirmRequired(call_id=tu_id, tool_name=tu_name, arguments=tu_args)
                decision = await tool_confirmation.wait(tu_id)
                _ = fut  # halte Referenz — fut wird in resolve() gesetzt
                if decision == "deny":
                    from hydrahive.tools import ToolResult
                    result, duration_ms = ToolResult.fail("Vom Benutzer abgelehnt"), 0
                    yield ToolUseResult(
                        call_id=tu_id, tool_name=tu_name, success=False,
                        output=None, error=result.error, duration_ms=0,
                    )
                    result_blocks.append(to_tool_result_block(tu_id, result))
                    continue

            result, _record_id, duration_ms = await execute_tool(
                tool_use=tu,
                allowed_tools=allowed_tools,
                ctx=ctx,
                parent_message_id=assistant_msg.id,
            )
            yield ToolUseResult(
                call_id=tu_id,
                tool_name=tu_name,
                success=result.success,
                output=result.output,
                error=result.error,
                duration_ms=duration_ms,
            )
            result_blocks.append(to_tool_result_block(tu_id, result))

        tool_msg = messages_db.append(session_id, "user", result_blocks)
        history.append(tool_msg)

    yield Error(
        f"Max-Iterationen ({MAX_ITERATIONS}) erreicht ohne Abschluss",
        metadata={"last_assistant_message": last_assistant_id},
    )


def _build_skills_block(agent: dict) -> str:
    """Kompakte Liste aller verfügbaren Skills für den Prompt-Header. Sagt dem
    Agent welche Skills es gibt und wann er sie laden soll. Body wird nur via
    `load_skill(name)` in den Kontext gezogen — Auto-Inject von Bodies wäre
    Token-Spam."""
    try:
        from hydrahive.skills import list_for_agent
    except Exception:
        return ""
    owner = agent.get("owner") or ""
    if not owner:
        return ""
    try:
        skills = list_for_agent(agent["id"], owner, disabled=list(agent.get("disabled_skills", [])))
    except Exception as e:
        logger.warning("Skills laden fehlgeschlagen: %s", e)
        return ""
    if not skills:
        return ""
    lines = ["## Verfügbare Skills",
             "Mit `load_skill(name)` lädst du den vollen Body in den Kontext.",
             "Skills können externe Quellen (URLs) deklarieren — diese rufst du mit "
             "`fetch_url(url)` ab; Auth wird automatisch via Credential-Profil-Match "
             "eingehängt (Token landet NICHT im Tool-Result)."]
    for s in skills:
        when = f" — when: {s.when_to_use}" if s.when_to_use else ""
        desc = f": {s.description}" if s.description else ""
        lines.append(f"- **{s.name}**{desc}{when}")
    return "\n".join(lines)


def _close_open_tool_uses(session_id: str, tool_uses: list[dict], reason: str) -> None:
    """Synthetic tool_result blocks for unfinished tool_uses, so Anthropic's API
    pairing-check passes on the next turn. Without this the session is poisoned
    and every subsequent send returns 400."""
    blocks = [
        {
            "type": "tool_result",
            "tool_use_id": tu.get("id", ""),
            "content": reason,
            "is_error": True,
        }
        for tu in tool_uses
        if tu.get("id")
    ]
    if blocks:
        messages_db.append(session_id, "user", blocks)
