from __future__ import annotations

from pathlib import Path

from hydrahive.modules.context import ModuleContext
from hydrahive.modules.manifest import ModuleManifest
from hydrahive.modules.registry import REGISTRY as MODREG, LoadedModule
from hydrahive.tools.base import Tool, ToolResult


async def _noop(args, ctx):
    return ToolResult.ok()


def _install_fake_module(monkeypatch, *, flag: bool, tool_name: str):
    from hydrahive import tools
    tool = Tool(name=tool_name, description="d", schema={}, execute=_noop)
    ctx = ModuleContext("fakemod")
    ctx.register_tool(tool)
    manifest = ModuleManifest(id="fakemod", name="F", version="1.0.0",
                              default_agent_tools=flag)
    lm = LoadedModule(name="fakemod", manifest=manifest, path=Path("/x"),
                      ctx=ctx, loaded=True)
    monkeypatch.setitem(MODREG, "fakemod", lm)
    tools.register_module_tools([tool])
    monkeypatch.setattr(tools, "_MODULE_TOOL_NAMES", set(), raising=False)  # reset-Schutz
    return tool


def test_flagged_module_tool_in_master_defaults(monkeypatch):
    from hydrahive import tools
    _install_fake_module(monkeypatch, flag=True, tool_name="fakemod_tool")
    try:
        from hydrahive.agents._defaults import DEFAULT_TOOLS
        assert "fakemod_tool" in DEFAULT_TOOLS["master"]
    finally:
        tools.register_module_tools([])


def test_unflagged_module_tool_not_in_defaults(monkeypatch):
    from hydrahive import tools
    _install_fake_module(monkeypatch, flag=False, tool_name="fakemod_tool2")
    try:
        from hydrahive.agents._defaults import DEFAULT_TOOLS
        assert "fakemod_tool2" not in DEFAULT_TOOLS["master"]
    finally:
        tools.register_module_tools([])


def test_master_defaults_deduped(monkeypatch):
    from hydrahive import tools
    # flagged module re-declares an existing core master default tool name
    _install_fake_module(monkeypatch, flag=True, tool_name="todo_write")
    try:
        from hydrahive.agents._defaults import DEFAULT_TOOLS
        master = DEFAULT_TOOLS["master"]
        assert master.count("todo_write") == 1   # not duplicated
    finally:
        tools.register_module_tools([])


def test_unregistered_module_tool_filtered(monkeypatch):
    # Flag gesetzt, aber Tool NICHT in tools.REGISTRY → muss rausgefiltert werden.
    from hydrahive import tools
    ctx = ModuleContext("ghost")
    ctx.register_tool(Tool(name="ghost_tool", description="d", schema={}, execute=_noop))
    manifest = ModuleManifest(id="ghost", name="G", version="1.0.0", default_agent_tools=True)
    monkeypatch.setitem(MODREG, "ghost",
                        LoadedModule(name="ghost", manifest=manifest, path=Path("/x"),
                                     ctx=ctx, loaded=True))
    from hydrahive.agents._defaults import DEFAULT_TOOLS
    assert "ghost_tool" not in DEFAULT_TOOLS["master"]
