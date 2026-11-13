"""LiteLLM muss mit unserem mcp<2 zusammen laufen, sobald Tools mitgeschickt werden.

Befund 13.11.2026 (Kunden-Mac, litellm 1.106.2 + mcp 1.30): litellm 1.106.0–1.108.3
importiert in completion() bei jedem Aufruf mit Tools seinen MCP-Gateway-Handler, und
der zieht `mcp.types.CacheableResult` – das gibt es erst in mcp 2.x. Folge: jeder Chat
über Ollama/LiteLLM scheiterte mit
„cannot import name 'CacheableResult' from 'mcp.types'“.

Der Test ruft das echte installierte litellm mit Tools und `mock_response` auf (kein
Netz) und prüft die Untergrenze im pyproject, damit ein Update kaputte Versionen ersetzt.
"""
from __future__ import annotations

import asyncio
import re
from importlib.metadata import version
from pathlib import Path

from packaging.version import Version

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
_TOOLS = [{
    "type": "function",
    "function": {"name": "ping", "description": "Test",
                 "parameters": {"type": "object", "properties": {}}},
}]


def test_litellm_call_with_tools_works_with_installed_mcp():
    import litellm

    async def _call():
        return await litellm.acompletion(
            model="ollama_chat/qwen-test",
            messages=[{"role": "user", "content": "hi"}],
            tools=_TOOLS,
            api_base="http://127.0.0.1:1",
            mock_response="ok",
        )

    resp = asyncio.run(_call())
    assert resp.choices[0].message.content == "ok"


def test_installed_mcp_stays_below_2():
    assert Version(version("mcp")) < Version("2")


def test_pyproject_excludes_broken_litellm_versions():
    text = _PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'"litellm>=([0-9.]+),<2"', text)
    assert m, "litellm-Pin im pyproject nicht gefunden"
    assert Version(m.group(1)) >= Version("1.108.4")
