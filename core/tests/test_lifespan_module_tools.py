from __future__ import annotations

import json


def test_module_tool_registered_after_load(mod_env):
    md = mod_env / "modules" / "tmod"
    (md / "backend").mkdir(parents=True)
    (md / "manifest.json").write_text(json.dumps(
        {"id": "tmod", "name": "T", "version": "1.0.0", "default_agent_tools": True}))
    (md / "backend" / "__init__.py").write_text(
        "from hydrahive.tools.base import Tool, ToolResult\n"
        "async def _x(a, c):\n"
        "    return ToolResult.ok('ok')\n"
        "TOOL = Tool(name='tmod_tool', description='d', schema={}, execute=_x,\n"
        "            prompt_hint='\\n\\nTMOD-HINT')\n"
        "def register(ctx):\n"
        "    ctx.register_tool(TOOL)\n"
    )
    from hydrahive.modules.loader import load_all
    from hydrahive.modules.registry import REGISTRY as MODREG
    from hydrahive import tools
    load_all()
    collected = [t for m in MODREG.values() if m.loaded and m.ctx for t in m.ctx.tools]
    tools.register_module_tools(collected)
    try:
        assert "tmod_tool" in tools.REGISTRY
    finally:
        tools.register_module_tools([])
