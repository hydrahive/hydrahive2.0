from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import AsyncIterator

from hydrahive.agents import config as agent_config
from hydrahive.agents._paths import ensure_workspace
from hydrahive.compaction import compact_session, should_compact
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.mcp import tool_bridge as mcp_bridge
from hydrahive.plugins import tool_bridge as plugin_bridge
from hydrahive.runner._call import CallResult, call_with_stream_or_fallback
from hydrahive.runner._runner_helpers import build_skills_block, close_open_tool_uses
from hydrahive.runner.context import extract_tool_uses, heal_orphan_tool_uses, to_anthropic_messages
from hydrahive.runner.dispatcher import execute_tool, to_tool_result_block
from hydrahive.runner.events import Done, Error, Event, IterationStart, ToolConfirmRequired, ToolUseResult, ToolUseStart
from hydrahive.runner import tool_confirmation
from hydrahive.tools import ToolContext, schemas_for

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 30
LOOP_DETECTION_WINDOW = 3


async def run(
    session_id: str,
    user_input: str | list,
    *,
    tool_config: dict | None = None,
    extra_system: str | None = None,
) -> AsyncIterator[Event]:
    session = sessions_db.get(session_id)
    if not session:
        yield Error(f"Session '{session_id}' nicht gefunden"); return

    agent = agent_config.get(session.agent_id)
    if not agent:
        yield Error(f"Agent '{session.agent_id}' nicht gefunden (Session ist verwaist)"); return
    if agent.get("status") != "active":
        yield Error(f"Agent '{agent['name']}' ist deaktiviert"); return

    workspace = ensure_workspace(agent)
    ctx = ToolContext(session_id=session_id, agent_id=agent["id"], user_id=session.user_id,
                     workspace=workspace, config=tool_config or {})

    base_system_prompt = agent_config.get_system_prompt(agent["id"])
    local_tools: list[str] = agent.get("tools", [])
    mcp_servers: list[str] = agent.get("mcp_servers", [])
    mcp_schemas = await mcp_bridge.schemas_for_servers(mcp_servers)
    plugin_schemas = plugin_bridge.schemas_for(local_tools)
    tool_schemas = schemas_for(local_tools) + mcp_schemas + plugin_schemas
    allowed_tools = local_tools + [s["name"] for s in mcp_schemas]

    if agent.get("longterm_memory"):
        from hydrahive.tools.datamining import TOOL_SEARCH, TOOL_SEMANTIC, TOOL_TODAY, TOOL_TIMELINE
        existing_tool_names = {s["name"] for s in tool_schemas}
        for _t in (TOOL_SEARCH, TOOL_SEMANTIC, TOOL_TODAY, TOOL_TIMELINE):
            if _t.name not in existing_tool_names:
                tool_schemas.append({"name": _t.name, "description": _t.description, "input_schema": _t.schema})
            if _t.name not in allowed_tools:
                allowed_tools.append(_t.name)
        base_system_prompt += (
            "\n\n## Langzeitgedächtnis — PFLICHT\n"
            "Du hast Zugriff auf eine Datenbank mit ALLEN vergangenen Sessions, Gesprächen und Tool-Calls.\n"
            "**Regel: Wenn du etwas nicht weißt oder eine Frage auf vergangene Ereignisse/Personen/Dinge verweist, "
            "rufe ZUERST datamining_search auf — bevor du antwortest oder spekulierst.**\n"
            "Beispiele wann du suchen musst:\n"
            "- Fragen wie 'wie geht es X?', 'was haben wir mit Y gemacht?', 'weißt du noch...?'\n"
            "- Unbekannte Namen, Begriffe oder Referenzen die aus früheren Gesprächen kommen könnten\n"
            "- Aufgaben die du fortsetzen sollst ohne klaren Kontext\n"
            "Tools:\n"
            "- `datamining_search(query, from_date, to_date)` — Volltextsuche; gibt nur neueste Events zurück, "
            "für historische Events immer from_date setzen (z.B. from_date='2026-01-01')!\n"
            "- `datamining_semantic(query)` — semantische Suche, findet auch ohne exakte Worte\n"
            "- `datamining_timeline(from_date, to_date)` — Zeitstrahl aller Sessions in einem Zeitraum, "
            "gruppiert nach Tag mit Gesprächsthemen — ideal für Langzeit-Analyse ohne Keyword\n"
            "- `datamining_today()` — was heute passiert ist\n"
        )

    messages_db.append(session_id, "user", user_input)

    last_assistant_id: str | None = None
    recent_tool_calls: list[str] = []
    total_input_tokens = total_output_tokens = total_cache_creation = total_cache_read = 0

    compact_model = agent.get("compact_model") or agent["llm_model"]
    compact_tool_limit = agent.get("compact_tool_result_limit")
    compact_reserve = agent.get("compact_reserve_tokens")
    compact_threshold_pct = int(agent.get("compact_threshold_pct", 100))

    for iteration in range(MAX_ITERATIONS):
        yield IterationStart(iteration=iteration + 1)

        history = messages_db.list_for_llm(session_id)
        effective_reserve = compact_reserve
        if effective_reserve is not None and compact_threshold_pct < 100:
            from hydrahive.compaction.tokens import context_window_for as _cwf
            window = _cwf(agent["llm_model"])
            effective_reserve = max(effective_reserve, window - int(window * compact_threshold_pct / 100))
        should_kwargs = {"reserve_tokens": effective_reserve} if effective_reserve is not None else {}
        if should_compact(history, agent["llm_model"], **should_kwargs):
            try:
                compact_kwargs = {} if compact_tool_limit is None else {"tool_result_limit": compact_tool_limit}
                await compact_session(session_id, model=compact_model, **compact_kwargs)
                history = messages_db.list_for_llm(session_id)
            except Exception as e:
                logger.warning("Compaction fehlgeschlagen: %s — fahre mit voller History fort", e)

        summary = messages_db.get_latest_summary(session_id)
        system_prompt = (f"[Bisherige Zusammenfassung]\n{summary}\n\n{base_system_prompt}"
                         if summary else base_system_prompt)
        skills_block = build_skills_block(agent)
        if skills_block:
            system_prompt = f"{system_prompt}\n\n{skills_block}"
        if extra_system:
            system_prompt = f"{extra_system}\n\n{system_prompt}"
        now = datetime.now().astimezone()
        date_block = (f"Aktuelles Datum/Uhrzeit (Server): "
                      f"{now.strftime('%Y-%m-%d %H:%M %Z')} ({now.strftime('%A')}). "
                      f"Verwende dieses Datum als Referenz, NICHT dein Trainings-Cutoff.")
        system_prompt = f"{date_block}\n\n{system_prompt}"

        healed_history = heal_orphan_tool_uses(history)
        anth_messages = to_anthropic_messages(healed_history)

        blocks: list[dict] = []
        stop_reason = iter_input_tokens = iter_output_tokens = iter_cache_creation = iter_cache_read = 0
        used_model = agent["llm_model"]
        stop_reason = ""
        try:
            models = [agent["llm_model"]] + list(agent.get("fallback_models", []) or [])
            async for item in call_with_stream_or_fallback(
                models=models, system_prompt=system_prompt, messages=anth_messages, tools=tool_schemas,
                temperature=agent.get("temperature", 0.7), max_tokens=agent.get("max_tokens", 4096),
            ):
                if isinstance(item, CallResult):
                    blocks = item.blocks; stop_reason = item.stop_reason
                    iter_input_tokens = item.input_tokens; iter_output_tokens = item.output_tokens
                    iter_cache_creation = item.cache_creation_tokens; iter_cache_read = item.cache_read_tokens
                    used_model = item.model or agent["llm_model"]
                    total_cache_creation += item.cache_creation_tokens
                    total_cache_read += item.cache_read_tokens
                else:
                    yield item
        except Exception as e:
            logger.exception("LLM-Call fehlgeschlagen")
            yield Error(f"LLM-Call fehlgeschlagen: {e}"); return

        total_input_tokens += iter_input_tokens
        total_output_tokens += iter_output_tokens

        assistant_msg = messages_db.append(
            session_id, "assistant", blocks,
            token_count=iter_output_tokens or None,
            metadata={"input_tokens": iter_input_tokens, "output_tokens": iter_output_tokens,
                      "cache_creation_tokens": iter_cache_creation, "cache_read_tokens": iter_cache_read,
                      "model": used_model, "stop_reason": stop_reason, "iteration": iteration + 1},
        )
        last_assistant_id = assistant_msg.id
        history.append(assistant_msg)

        tool_uses = extract_tool_uses(blocks)

        if stop_reason == "max_tokens":
            if tool_uses:
                close_open_tool_uses(session_id, tool_uses, "Abgebrochen: max_tokens-Limit überschritten")
            yield Error(
                f"max_tokens ({agent.get('max_tokens', 4096)}) erreicht — Antwort abgeschnitten. "
                "Tool-Argumente sind unvollständig. Erhöhe max_tokens oder formuliere die Aufgabe kürzer.",
                metadata={"stop_reason": stop_reason, "message_id": assistant_msg.id},
            ); return

        if not tool_uses:
            yield Done(message_id=assistant_msg.id, iterations=iteration + 1,
                       input_tokens=total_input_tokens, output_tokens=total_output_tokens,
                       cache_creation_tokens=total_cache_creation, cache_read_tokens=total_cache_read)
            return

        signature = "|".join(f"{tu.get('name')}:{json.dumps(tu.get('input', {}), sort_keys=True)}" for tu in tool_uses)
        recent_tool_calls.append(signature)
        recent_tool_calls = recent_tool_calls[-LOOP_DETECTION_WINDOW:]
        if len(recent_tool_calls) == LOOP_DETECTION_WINDOW and len(set(recent_tool_calls)) == 1:
            close_open_tool_uses(session_id, tool_uses, "Abgebrochen: Loop erkannt, Agent wiederholt sich")
            yield Error(f"Loop erkannt — Agent ruft seit {LOOP_DETECTION_WINDOW} Iterationen die exakt gleichen Tools auf.",
                        metadata={"signature": signature[:200], "message_id": assistant_msg.id})
            return

        result_blocks: list[dict] = []
        require_confirm = bool(agent.get("require_tool_confirm", False))
        for tu in tool_uses:
            tu_id = tu.get("id", ""); tu_name = tu.get("name", ""); tu_args = tu.get("input", {}) or {}
            yield ToolUseStart(call_id=tu_id, tool_name=tu_name, arguments=tu_args)

            if require_confirm:
                fut = tool_confirmation.register(tu_id)
                yield ToolConfirmRequired(call_id=tu_id, tool_name=tu_name, arguments=tu_args)
                decision = await tool_confirmation.wait(tu_id)
                _ = fut
                if decision == "deny":
                    from hydrahive.tools import ToolResult
                    result, duration_ms = ToolResult.fail("Vom Benutzer abgelehnt"), 0
                    yield ToolUseResult(call_id=tu_id, tool_name=tu_name, success=False,
                                        output=None, error=result.error, duration_ms=0)
                    result_blocks.append(to_tool_result_block(tu_id, result, ctx, tu_name)); continue

            result, _record_id, duration_ms = await execute_tool(
                tool_use=tu, allowed_tools=allowed_tools, ctx=ctx, parent_message_id=assistant_msg.id)
            yield ToolUseResult(call_id=tu_id, tool_name=tu_name, success=result.success,
                                output=result.output, error=result.error, duration_ms=duration_ms)
            result_blocks.append(to_tool_result_block(tu_id, result, ctx, tu_name))

        tool_msg = messages_db.append(session_id, "user", result_blocks)
        history.append(tool_msg)

    yield Error(f"Max-Iterationen ({MAX_ITERATIONS}) erreicht ohne Abschluss",
                metadata={"last_assistant_message": last_assistant_id})
