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
from hydrahive.runner.integrity import IntegrityState
from hydrahive.settings import settings
from hydrahive.tools import ToolContext, ToolResult
from hydrahive.tools._discord_admin_confirm import (
    TOOL_MEMBER as _DC_MEMBER, TOOL_SERVER as _DC_SERVER,
    confirm_reason as discord_admin_confirm_reason,
)
from hydrahive.tools._observations import (
    HOOK_POST_TOOL_FAILURE,
    HOOK_POST_TOOL_USE,
    record_observation,
)
from hydrahive.tools._protected_paths import shell_confirm_reason

# Tools, deren Wirkung nicht rückgängig zu machen ist: immer Bestätigung durch den
# Benutzer, auch ohne require_tool_confirm am Agenten (ohne Antwort = nicht ausgeführt).
ALWAYS_CONFIRM: dict[str, str] = {
    "discord_delete": "Löschen in Discord lässt sich nicht rückgängig machen.",
}
DISCORD_ADMIN_TOOLS = frozenset({_DC_SERVER, _DC_MEMBER})
# Ohne Antwort ist nicht „abgelehnt“: der Agent soll den Unterschied kennen.
_NOT_RUN = {
    "deny": "Vom Benutzer abgelehnt",
    "timeout": "Keine Antwort auf die Bestätigung – nicht ausgeführt",
}


def _confirm_timeout(ctx: ToolContext) -> float | None:
    """Chat-Fenster (chat/delegation): warten, bis jemand entscheidet (Standard).
    Ohne Fenster (Zeitplan, Messenger, ask_agent): Limit, danach „keine Antwort“.
    docs/specs/harakiri-confirm-noise.md, Punkt 3."""
    if ctx.origin in ("chat", "delegation"):
        return settings.tool_confirm_timeout_chat
    return settings.tool_confirm_timeout


async def process_tool_uses(
    tool_uses: list[dict],
    *,
    ctx: ToolContext,
    allowed_tools: list[str],
    parent_message_id: str,
    require_confirm: bool,
    tool_result_max_chars: int,
    iteration: int | None = None,
    integrity_state: IntegrityState | None = None,
    sink: list[dict] | None = None,
) -> AsyncIterator[Event | list[dict]]:
    """Führt alle tool_uses einer Iteration aus, yields Events.
    Letzter yield ist die fertige `result_blocks: list[dict]`.

    `sink`: Liste des Aufrufers, in die jeder fertige Block SOFORT wandert.
    Wird der Lauf mitten in der Runde gestoppt, kennt der Runner so die schon
    fertigen Ergebnisse und speichert sie (runner/_runner_cancel.py).
    """
    result_blocks: list[dict] = sink if sink is not None else []
    for tu in tool_uses:
        tu_id = tu.get("id", "")
        tu_name = tu.get("name", "")
        tu_args = tu.get("input", {}) or {}
        yield ToolUseStart(call_id=tu_id, tool_name=tu_name, arguments=tu_args)

        # Harakiri-Schutz: auch ohne globales require_confirm verlangt ein
        # shell_exec, das in einen geschützten Pfad schreibt oder ein Geheimnis
        # liest, eine Bestätigung — pro Call, mit Begründung im Event.
        confirm_reason: str | None = None
        if tu_name == "shell_exec":
            confirm_reason = shell_confirm_reason(tu_args.get("cmd", "") or "")
        elif tu_name in ALWAYS_CONFIRM:
            confirm_reason = ALWAYS_CONFIRM[tu_name]
        elif tu_name in DISCORD_ADMIN_TOOLS:
            # Serververwaltung: Löschen, Kick, Bann, Rechte → Bestätigung je nach Aktion.
            confirm_reason = discord_admin_confirm_reason(tu_name, tu_args)
        needs_confirm = require_confirm or confirm_reason is not None

        if needs_confirm:
            tool_confirmation.register(
                tu_id, session_id=ctx.session_id, tool_name=tu_name,
                arguments=tu_args, reason=confirm_reason,
            )
            yield ToolConfirmRequired(
                call_id=tu_id, tool_name=tu_name, arguments=tu_args, reason=confirm_reason
            )
            decision = await tool_confirmation.wait(tu_id, timeout=_confirm_timeout(ctx))
            if decision != "approve":
                result = ToolResult.fail(_NOT_RUN[decision])
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
        # execute_tool hat Secrets bereits an der zentralen Engstelle geschwärzt.
        # Integrity erhält daher ausschließlich das redigierte Resultat.
        if integrity_state is not None:
            integrity_state.record_tool(tu_name, tu_args, result)
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
