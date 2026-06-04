from __future__ import annotations

from hydrahive.modules.context import ModuleContext
from hydrahive.tools.base import Tool, ToolResult


async def _noop(args, ctx):
    return ToolResult.ok()


def test_register_tool_collects():
    ctx = ModuleContext("demo")
    t = Tool(name="demo_tool", description="d", schema={}, execute=_noop)
    ctx.register_tool(t)
    assert ctx.tools == [t]


def test_tools_default_empty():
    assert ModuleContext("demo").tools == []
