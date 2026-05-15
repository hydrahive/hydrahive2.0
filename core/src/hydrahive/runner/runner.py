from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncIterator

from hydrahive.agents import config as agent_config
from hydrahive.agents._defaults import (
    DEFAULT_COMPACT_THRESHOLD_PCT,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_MAX_TOKENS,
)
from hydrahive.agents._paths import ensure_workspace
from hydrahive.compaction import compact_session, should_compact
from hydrahive.compaction.tokens import context_window_for
from hydrahive.db import errors_log
from hydrahive.db import llm_calls as llm_calls_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.llm._pricing import cost_micros, provider_from_model
from hydrahive.mcp import tool_bridge as mcp_bridge
from hydrahive.plugins import tool_bridge as plugin_bridge
from hydrahive.runner._runner_helpers import close_open_tool_uses
from hydrahive.runner._runner_iter import (
    IterationResult,
    build_system_prompts,
    prepare_history,
    stream_llm_call,
)
from hydrahive.runner._runner_setup import inject_longterm_memory
from hydrahive.runner._runner_tools import process_tool_uses
from hydrahive.runner.context import extract_tool_uses, heal_orphan_tool_uses, to_anthropic_messages
from hydrahive.runner.events import Done, Error, Event, IterationStart
from hydrahive.tools import ToolContext, schemas_for
from hydrahive.tools._compress import compress_session
from hydrahive.tools._sessions import session_end, session_start

logger = logging.getLogger(__name__)

# Modul-Default für Backwards-Compat. Per-Agent-Override (siehe `run()`)
# gewinnt — Agent-Configs können `max_iterations` setzen.
MAX_ITERATIONS = DEFAULT_MAX_ITERATIONS
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
                     workspace=workspace, config=tool_config or {},
                     project_id=(tool_config or {}).get("project_id"))

    # Session-Lifecycle: start
    _first_prompt = user_input if isinstance(user_input, str) else None
    session_start(
        agent["id"], session_id,
        project=(tool_config or {}).get("project_id"),
        model=agent.get("llm_model"),
        first_prompt=_first_prompt,
    )

    base_system_prompt = agent_config.get_system_prompt(agent["id"])

    local_tools: list[str] = agent.get("tools", [])
    mcp_servers: list[str] = agent.get("mcp_servers", [])
    mcp_schemas = await mcp_bridge.schemas_for_servers(mcp_servers)
    plugin_schemas = plugin_bridge.schemas_for(local_tools)
    tool_schemas = schemas_for(local_tools) + mcp_schemas + plugin_schemas
    allowed_tools = local_tools + [s["name"] for s in mcp_schemas]

    if agent.get("longterm_memory"):
        base_system_prompt = inject_longterm_memory(base_system_prompt, tool_schemas, allowed_tools)

    messages_db.append(session_id, "user", user_input)

    last_assistant_id: str | None = None
    recent_tool_calls: list[str] = []
    total_input_tokens = total_output_tokens = total_cache_creation = total_cache_read = 0

    compact_model = agent.get("compact_model") or agent["llm_model"]
    compact_tool_limit = agent.get("compact_tool_result_limit")
    compact_reserve = agent.get("compact_reserve_tokens")
    compact_threshold_pct = int(agent.get("compact_threshold_pct", DEFAULT_COMPACT_THRESHOLD_PCT))
    tool_result_max_chars = int(agent.get("tool_result_max_chars") or 0)
    cache_ttl: str = agent.get("cache_ttl") or "1h"
    max_iterations = int(agent.get("max_iterations") or DEFAULT_MAX_ITERATIONS)

    for iteration in range(max_iterations):
        yield IterationStart(iteration=iteration + 1)

        history = await prepare_history(
            session_id, model=agent["llm_model"], compact_model=compact_model,
            compact_tool_limit=compact_tool_limit, compact_reserve=compact_reserve,
            compact_threshold_pct=compact_threshold_pct,
        )

        stable_system, volatile_system, summary_system = build_system_prompts(
            base_system_prompt,
            extra_system=extra_system,
            workspace=workspace,
            summary=messages_db.get_latest_summary(session_id),
        )

        # Pro-Session-Override (Chat-Header-Switcher) gewinnt vor Agent-Default.
        # Re-Read aus DB damit ein Switch ohne Server-Restart sofort greift.
        _fresh_session = sessions_db.get(session_id)
        model_override = (_fresh_session.metadata or {}).get("model_override") if _fresh_session else None
        reasoning_effort = (_fresh_session.metadata or {}).get("reasoning_effort") if _fresh_session else None
        primary_model = model_override or agent["llm_model"]

        result: IterationResult | None = None
        t0 = time.monotonic()
        try:
            async for item in stream_llm_call(
                primary_model=primary_model,
                fallback_models=agent.get("fallback_models", []) or [],
                stable_system=stable_system, volatile_system=volatile_system,
                summary_system=summary_system, cache_ttl=cache_ttl,
                anth_messages=to_anthropic_messages(heal_orphan_tool_uses(history)),
                tool_schemas=tool_schemas,
                temperature=agent.get("temperature", 0.7),
                max_tokens=agent.get("max_tokens", DEFAULT_MAX_TOKENS),
                reasoning_effort=reasoning_effort,
            ):
                if isinstance(item, IterationResult):
                    result = item
                else:
                    yield item
        except Exception as e:
            logger.exception("LLM-Call fehlgeschlagen")
            errors_log.record(
                source="runner.llm_call", exc=e,
                session_id=session_id, agent_id=agent["id"], user_id=ctx.user_id,
                context={"model": primary_model, "iteration": iteration + 1,
                         "reasoning_effort": reasoning_effort},
            )
            session_end(agent["id"], session_id, status="abandoned")
            yield Error(f"LLM-Call fehlgeschlagen: {e}"); return

        assert result is not None
        total_ms = int((time.monotonic() - t0) * 1000)
        total_input_tokens += result.input_tokens
        total_output_tokens += result.output_tokens
        total_cache_creation += result.cache_creation_tokens
        total_cache_read += result.cache_read_tokens

        # Token-Audit (#129): pro LLM-Call eine Zeile in llm_calls
        try:
            _provider = provider_from_model(result.used_model)
            llm_calls_db.insert(llm_calls_db.LlmCall(
                session_id=session_id,
                agent_id=agent["id"],
                user_id=ctx.user_id,
                provider=_provider,
                model=result.used_model,
                temperature=agent.get("temperature", 0.7),
                max_tokens=agent.get("max_tokens", DEFAULT_MAX_TOKENS),
                reasoning_effort=reasoning_effort,
                prompt_tokens=result.input_tokens,
                completion_tokens=result.output_tokens,
                cache_read_tokens=result.cache_read_tokens,
                cache_creation_tokens=result.cache_creation_tokens,
                stop_reason=result.stop_reason,
                ttft_ms=None,
                total_ms=total_ms,
                cost_micros=cost_micros(
                    _provider, result.used_model,
                    prompt_tokens=result.input_tokens,
                    completion_tokens=result.output_tokens,
                    cache_read_tokens=result.cache_read_tokens,
                    cache_creation_tokens=result.cache_creation_tokens,
                ),
                turn_in_session=iteration + 1,
            ))
        except Exception:
            logger.exception("llm_calls-Insert fehlgeschlagen — Telemetrie verloren, Lauf läuft weiter")

        assistant_msg = messages_db.append(
            session_id, "assistant", result.blocks,
            token_count=result.output_tokens or None,
            metadata={"input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
                      "cache_creation_tokens": result.cache_creation_tokens,
                      "cache_read_tokens": result.cache_read_tokens,
                      "model": result.used_model, "stop_reason": result.stop_reason,
                      "iteration": iteration + 1},
        )
        last_assistant_id = assistant_msg.id
        history.append(assistant_msg)

        tool_uses = extract_tool_uses(result.blocks)

        if result.stop_reason == "max_tokens":
            if tool_uses:
                close_open_tool_uses(session_id, tool_uses, "Abgebrochen: max_tokens-Limit überschritten")
            session_end(agent["id"], session_id, status="abandoned")
            yield Error(
                f"max_tokens ({agent.get('max_tokens', DEFAULT_MAX_TOKENS)}) erreicht — Antwort abgeschnitten. "
                "Tool-Argumente sind unvollständig. Erhöhe max_tokens oder formuliere die Aufgabe kürzer.",
                metadata={"stop_reason": result.stop_reason, "message_id": assistant_msg.id},
            ); return

        if not tool_uses:
            session_end(agent["id"], session_id, status="completed")
            # Compress-Pipeline: fire-and-forget — Done nicht blockieren.
            # Wrap mit errors_log.capture damit Crashes nicht still verschwinden.
            async def _safe_compress(_aid: str, _sid: str, _model: str) -> None:
                with errors_log.capture(
                    source="runner.compress_bg",
                    session_id=_sid, agent_id=_aid,
                    context={"model": _model},
                    reraise=False,
                ):
                    await compress_session(_aid, _sid, model=_model)
            asyncio.create_task(
                _safe_compress(agent["id"], session_id, agent["llm_model"])
            )
            yield Done(message_id=assistant_msg.id, iterations=iteration + 1,
                       input_tokens=total_input_tokens, output_tokens=total_output_tokens,
                       cache_creation_tokens=total_cache_creation, cache_read_tokens=total_cache_read)
            return

        signature = "|".join(f"{tu.get('name')}:{json.dumps(tu.get('input', {}), sort_keys=True)}" for tu in tool_uses)
        recent_tool_calls.append(signature)
        recent_tool_calls = recent_tool_calls[-LOOP_DETECTION_WINDOW:]
        if len(recent_tool_calls) == LOOP_DETECTION_WINDOW and len(set(recent_tool_calls)) == 1:
            close_open_tool_uses(session_id, tool_uses, "Abgebrochen: Loop erkannt, Agent wiederholt sich")
            session_end(agent["id"], session_id, status="abandoned")
            yield Error(f"Loop erkannt — Agent ruft seit {LOOP_DETECTION_WINDOW} Iterationen die exakt gleichen Tools auf.",
                        metadata={"signature": signature[:200], "message_id": assistant_msg.id})
            return

        # Tool-Use-Loop: in Sub-Modul. Letzter yield ist result_blocks.
        result_blocks: list[dict] = []
        async for item in process_tool_uses(
            tool_uses, ctx=ctx, allowed_tools=allowed_tools,
            parent_message_id=assistant_msg.id,
            require_confirm=bool(agent.get("require_tool_confirm", False)),
            tool_result_max_chars=tool_result_max_chars,
            iteration=iteration + 1,
        ):
            if isinstance(item, list):
                result_blocks = item
            else:
                yield item

        tool_msg = messages_db.append(session_id, "user", result_blocks)
        history.append(tool_msg)

    # Pre-Resume-Compaction (#143): Wenn die History bei max_iterations noch
    # groß ist, einmal compactes bevor wir pausieren. Damit der "Weitermachen"-
    # Resume nicht direkt wieder nach 16 Iter knallt. Reserve = window/2
    # ⇒ Trigger bei History > 50% Window.
    if compact_threshold_pct < 100:
        try:
            _history = messages_db.list_for_llm(session_id)
            _window = context_window_for(agent["llm_model"])
            if should_compact(_history, agent["llm_model"], reserve_tokens=_window // 2):
                _kwargs = {} if compact_tool_limit is None else {"tool_result_limit": compact_tool_limit}
                await compact_session(
                    session_id, model=compact_model,
                    triggered_by="max_iterations_resume",
                    trigger_threshold_pct=50,
                    **_kwargs,
                )
        except Exception:
            logger.exception("Pre-resume Compaction fehlgeschlagen — Resume startet mit voller History")

    session_end(agent["id"], session_id, status="paused")
    yield Error(f"Max-Iterationen ({max_iterations}) erreicht ohne Abschluss",
                metadata={"kind": "max_iterations",
                          "last_assistant_message": last_assistant_id})
