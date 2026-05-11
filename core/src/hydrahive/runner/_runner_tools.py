"""Runner — Tool-Use-Loop pro LLM-Iteration.

Verarbeitet die tool_use-Blöcke aus der Assistant-Antwort: Confirmation
einholen falls nötig, Tool ausführen, Observation aufzeichnen, Result-
Block bauen. Async-Generator: yields Events, gibt result_blocks zurück.
"""
from __future__ import annotations

from typing import AsyncIterator

from hydrahive.runner import tool_confirmation
from hydrahive.runner.dispatcher import execute_tool, to_tool_result_block
from hydrahive.runner.events import Event, ToolConfirmRequired, ToolUseResult, ToolUseStart
from hydrahive.tools import ToolContext, ToolResult
from hydrahive.tools._observations import (
    HOOK_POST_TOOL_FAILURE,
    HOOK_POST_TOOL_USE,
    record_observation,
)


async def process_tool_uses(
    tool_uses: list[dict],
    *,
    ctx: ToolContext,
    allowed_tools: list[str],
    parent_message_id: str,
    require_confirm: bool,
    tool_result_max_chars: int,
    iteration: int | None = None,
) -> AsyncIterator[Event | list[dict]]:
    """Führt alle tool_uses einer Iteration aus, yields Events.
    Letzter yield ist die fertige `result_blocks: list[dict]`.
    """
    result_blocks: list[dict] = []
    for tu in tool_uses:
        tu_id = tu.get("id", "")
        tu_name = tu.get("name", "")
        tu_args = tu.get("input", {}) or {}
        yield ToolUseStart(call_id=tu_id, tool_name=tu_name, arguments=tu_args)

        if require_confirm:
            fut = tool_confirmation.register(tu_id)
            yield ToolConfirmRequired(call_id=tu_id, tool_name=tu_name, arguments=tu_args)
            decision = await tool_confirmation.wait(tu_id)
            _ = fut
            if decision == "deny":
                result = ToolResult.fail("Vom Benutzer abgelehnt")
                yield ToolUseResult(
                    call_id=tu_id, tool_name=tu_name, success=False,
                    output=None, error=result.error, duration_ms=0,
                )
                # Kein record_observation — User-Ablehnung ist kein Tool-Ergebnis,
                # sondern ein Kontroll-Ereignis.
                result_blocks.append(to_tool_result_block(tu_id, result, ctx, tu_name))
                continue

        result, record_id, duration_ms = await execute_tool(
            tool_use=tu, allowed_tools=allowed_tools, ctx=ctx,
            parent_message_id=parent_message_id, iteration=iteration,
        )
        record_observation(
            agent_id=ctx.agent_id, session_id=ctx.session_id,
            tool_name=tu_name, tool_input=tu_args,
            tool_output=result.output if result.success else result.error,
            hook_type=HOOK_POST_TOOL_USE if result.success else HOOK_POST_TOOL_FAILURE,
        )
        yield ToolUseResult(
            call_id=tu_id, tool_name=tu_name, success=result.success,
            output=result.output, error=result.error, duration_ms=duration_ms,
        )
        result_blocks.append(
            to_tool_result_block(
                tu_id, result, ctx, tu_name,
                max_chars=tool_result_max_chars, record_id=record_id,
            )
        )

    yield result_blocks
