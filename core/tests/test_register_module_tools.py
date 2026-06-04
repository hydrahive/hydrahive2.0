from __future__ import annotations

from hydrahive.tools.base import Tool, ToolResult


async def _noop(args, ctx):
    return ToolResult.ok()


def _tool(name):
    return Tool(name=name, description="d", schema={}, execute=_noop)


def test_module_tool_lands_in_registry():
    from hydrahive import tools
    tools.register_module_tools([_tool("mod_a")])
    try:
        assert "mod_a" in tools.REGISTRY
    finally:
        tools.register_module_tools([])  # cleanup


def test_reregister_replaces_without_duplicates():
    from hydrahive import tools
    tools.register_module_tools([_tool("mod_a")])
    tools.register_module_tools([_tool("mod_b")])  # neuer Satz
    try:
        assert "mod_b" in tools.REGISTRY
        assert "mod_a" not in tools.REGISTRY  # alter Modul-Tool entfernt
    finally:
        tools.register_module_tools([])


def test_empty_clears_module_tools():
    from hydrahive import tools
    tools.register_module_tools([_tool("mod_a")])
    tools.register_module_tools([])
    assert "mod_a" not in tools.REGISTRY


def test_core_tools_untouched():
    from hydrahive import tools
    tools.register_module_tools([_tool("mod_a")])
    try:
        assert "shell_exec" in tools.REGISTRY  # Core-Tool bleibt
    finally:
        tools.register_module_tools([])


def test_reset_restores_shadowed_core_tool():
    from hydrahive import tools
    original = tools.REGISTRY["shell_exec"]
    shadow = _tool("shell_exec")  # module tool reusing a core name
    tools.register_module_tools([shadow])
    assert tools.REGISTRY["shell_exec"] is shadow      # module overrides while active
    tools.register_module_tools([])                    # reset
    assert tools.REGISTRY["shell_exec"] is original    # core tool restored, not deleted
