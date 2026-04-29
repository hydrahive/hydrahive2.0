from __future__ import annotations

import logging
import time
from dataclasses import asdict

from hydrahive.db import tools as tools_db
from hydrahive.mcp import tool_bridge as mcp_bridge
from hydrahive.plugins import tool_bridge as plugin_bridge
from hydrahive.tools import REGISTRY, ToolContext, ToolResult

logger = logging.getLogger(__name__)


async def execute_tool(
    tool_use: dict,
    allowed_tools: list[str],
    ctx: ToolContext,
    parent_message_id: str,
) -> tuple[ToolResult, str, int]:
    """Execute a single tool_use block. Returns (result, db_call_id, duration_ms).

    Persists a `tool_calls` record. Catches all exceptions and turns them
    into ToolResult.fail — the LLM gets feedback instead of the runner crashing.
    """
    tool_name = tool_use.get("name", "")
    args = tool_use.get("input", {}) or {}

    # Always persist the call attempt — even if it fails validation.
    record = tools_db.create(parent_message_id, tool_name, args)
    start = time.monotonic()

    if tool_name not in allowed_tools:
        result = ToolResult.fail(
            f"Tool '{tool_name}' für diesen Agent nicht erlaubt."
        )
    elif tool_name.startswith(mcp_bridge.PREFIX):
        # MCP-Tool: an Bridge dispatchen, Result in unser Format wandeln
        try:
            mcp_res = await mcp_bridge.call(tool_name, args)
        except Exception as e:
            logger.exception("MCP-Tool '%s' crashte", tool_name)
            result = ToolResult.fail(f"MCP-Crash: {type(e).__name__}: {e}")
        else:
            if mcp_res is None:
                result = ToolResult.fail(f"MCP-Routing fehlgeschlagen für '{tool_name}'")
            else:
                output_text = mcp_res.content[0].get("text", "") if mcp_res.content else ""
                result = ToolResult(
                    success=mcp_res.success,
                    output=output_text or None,
                    error=mcp_res.error,
                )
    elif tool_name.startswith(plugin_bridge.PREFIX):
        plugin_res = await plugin_bridge.call(tool_name, args, ctx)
        result = plugin_res or ToolResult.fail(
            f"Plugin-Routing fehlgeschlagen für '{tool_name}'"
        )
    elif tool_name not in REGISTRY:
        result = ToolResult.fail(f"Tool '{tool_name}' weder lokal noch MCP gefunden")
    else:
        tool = REGISTRY[tool_name]
        try:
            result = await tool.execute(args, ctx)
        except Exception as e:
            logger.exception("Tool '%s' crashte", tool_name)
            result = ToolResult.fail(f"Tool-Crash: {type(e).__name__}: {e}")

    duration_ms = int((time.monotonic() - start) * 1000)
    tools_db.finish(
        record.id,
        result=asdict(result),
        status="success" if result.success else "error",
        duration_ms=duration_ms,
    )
    return result, record.id, duration_ms


def to_tool_result_block(tool_use_id: str, result: ToolResult) -> dict:
    """Build the Anthropic `tool_result` content block from a ToolResult."""
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": result.to_llm(),
        "is_error": not result.success,
    }
