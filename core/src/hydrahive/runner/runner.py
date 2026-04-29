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
    ToolUseResult,
    ToolUseStart,
)
from hydrahive.tools import ToolContext, schemas_for

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 30
LOOP_DETECTION_WINDOW = 3  # 3× identisches Tool-Use → Abbruch


async def run(session_id: str, user_input: str, *, tool_config: dict | None = None) -> AsyncIterator[Event]:
    """Run one user turn against the agent. Yields events; persists state.

    Caller is responsible for SSE-encoding the events for HTTP. Errors are
    yielded as Error-events (not raised) so the stream stays well-formed.
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

    for iteration in range(MAX_ITERATIONS):
        yield IterationStart(iteration=iteration + 1)

        # Build LLM history (resolves through latest compaction)
        history = messages_db.list_for_llm(session_id)
        if should_compact(history, agent["llm_model"]):
            try:
                await compact_session(session_id, model=agent["llm_model"])
                history = messages_db.list_for_llm(session_id)
            except Exception as e:
                logger.warning("Compaction fehlgeschlagen: %s — fahre mit voller History fort", e)

        summary = messages_db.get_latest_summary(session_id)
        system_prompt = (
            f"[Bisherige Zusammenfassung]\n{summary}\n\n{base_system_prompt}"
            if summary else base_system_prompt
        )

        healed_history = heal_orphan_tool_uses(history)
        anth_messages = to_anthropic_messages(healed_history)

        blocks: list[dict] = []
        stop_reason = ""
        iter_input_tokens = 0
        iter_output_tokens = 0
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
            metadata={"input_tokens": iter_input_tokens, "output_tokens": iter_output_tokens},
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
        for tu in tool_uses:
            yield ToolUseStart(
                call_id=tu.get("id", ""),
                tool_name=tu.get("name", ""),
                arguments=tu.get("input", {}) or {},
            )
            result, _record_id, duration_ms = await execute_tool(
                tool_use=tu,
                allowed_tools=allowed_tools,
                ctx=ctx,
                parent_message_id=assistant_msg.id,
            )
            yield ToolUseResult(
                call_id=tu.get("id", ""),
                tool_name=tu.get("name", ""),
                success=result.success,
                output=result.output,
                error=result.error,
                duration_ms=duration_ms,
            )
            result_blocks.append(to_tool_result_block(tu.get("id", ""), result))

        tool_msg = messages_db.append(session_id, "user", result_blocks)
        history.append(tool_msg)

    yield Error(
        f"Max-Iterationen ({MAX_ITERATIONS}) erreicht ohne Abschluss",
        metadata={"last_assistant_message": last_assistant_id},
    )


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
