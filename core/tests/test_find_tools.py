"""Katalog Etappe 3, Aufgabe 3: das Tool find_tools (Spec S7, K3)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from hydrahive.tools.base import ToolContext


def _ctx(tmp_path: Path) -> ToolContext:
    return ToolContext(session_id="s1", agent_id="a1", user_id="u1", workspace=tmp_path)


@pytest.fixture
def frisch():
    from hydrahive.catalog import _store
    _store.reset_store()
    yield
    _store.reset_store()


def _run(tmp_path, query, allowed, monkeypatch, **extra):
    from hydrahive.tools import find_tools
    monkeypatch.setattr(find_tools, "_allowed_for", lambda ctx: set(allowed))
    return asyncio.run(find_tools.TOOL.execute({"query": query, **extra}, _ctx(tmp_path)))


def test_liefert_name_beschreibung_schema_und_hinweis(frisch, tmp_path, monkeypatch):
    res = _run(tmp_path, "Bild erzeugen", {"generate_image", "fetch_url", "web_search"}, monkeypatch)
    assert res.success, res.error
    first = res.output["results"][0]
    assert first["name"] == "generate_image"
    assert first["description"] and first["input_schema"]["type"] == "object"
    assert "prompt" in first["input_schema"]["properties"]
    assert "run_tool(" in res.output["hint"]


def test_gesperrtes_tool_nicht_im_ergebnis_auch_nicht_als_text(frisch, tmp_path, monkeypatch):
    res = _run(tmp_path, "Mail schicken", {"fetch_url", "web_search", "file_read"}, monkeypatch)
    assert res.success
    blob = json.dumps(res.output, ensure_ascii=False)
    assert "send_mail" not in blob and "Sendet eine E-Mail" not in blob


def test_leere_anfrage_wird_abgelehnt(frisch, tmp_path, monkeypatch):
    res = _run(tmp_path, "   ", {"fetch_url"}, monkeypatch)
    assert not res.success and "Suchbegriff" in (res.error or "")


def test_limit_wird_begrenzt(frisch, tmp_path, monkeypatch):
    from hydrahive.tools import REGISTRY
    res = _run(tmp_path, "Datei", set(REGISTRY), monkeypatch, limit=500)
    assert res.success and len(res.output["results"]) <= 10


def test_entferntes_tool_wird_nicht_mehr_angeboten(frisch, tmp_path, monkeypatch):
    """Review-Fokus 4: find_tools baut den Index bei Änderung der Tool-Menge neu, ein entferntes Tool verschwindet."""
    from hydrahive.tools import REGISTRY
    from hydrahive.tools.base import Tool, ToolResult

    async def _x(args, ctx):
        return ToolResult.ok("x")
    monkeypatch.setitem(REGISTRY, "kolibri_pfleger", Tool(
        name="kolibri_pfleger", description="Pflegt Kolibris im Gewächshaus",
        schema={"type": "object", "properties": {}}, execute=_x))
    res = _run(tmp_path, "Kolibris pflegen", {"kolibri_pfleger"}, monkeypatch)
    assert [r["name"] for r in res.output["results"]] == ["kolibri_pfleger"]
    monkeypatch.delitem(REGISTRY, "kolibri_pfleger")
    res = _run(tmp_path, "Kolibris pflegen", {"kolibri_pfleger"}, monkeypatch)
    assert res.output["results"] == []


def test_find_tools_in_registry_aber_in_keiner_default_liste():
    from hydrahive.agents._defaults import DEFAULT_TOOLS
    from hydrahive.tools import REGISTRY
    assert "find_tools" in REGISTRY
    for typ, tools in DEFAULT_TOOLS.items():
        assert "find_tools" not in tools, f"find_tools in DEFAULT_TOOLS[{typ}]"
    src = Path(__file__).resolve().parents[1] / "src" / "hydrahive"
    erlaubt = {"find_tools.py", "_run_tool_unwrap.py", "agents.py", "index.py"}
    for f in src.rglob("*.py"):
        if f.name in erlaubt:
            continue
        code = "\n".join(l for l in f.read_text().splitlines() if not l.lstrip().startswith("#"))
        assert '"find_tools"' not in code, f"find_tools in {f}"


def test_find_tools_im_editor_ausgeblendet():
    from hydrahive.api.routes import agents
    assert {"run_tool", "find_tools"} <= set(agents._HIDDEN_IN_EDITOR)


def test_allowed_kommt_aus_effective_tool_names(monkeypatch, tmp_path):
    """Die Freigabe des Laufs ist effective_tool_names (S6), nicht der Katalog."""
    from hydrahive.tools import find_tools
    seen = {}

    def fake_effective(agent, *, username, project, pool=None):
        seen["called"] = (agent.get("id"), username)
        return ["file_read"]
    monkeypatch.setattr(find_tools, "effective_tool_names", fake_effective)
    monkeypatch.setattr(find_tools, "_agent_for", lambda ctx: {"id": "a1", "tools": ["file_read", "send_mail"]})
    monkeypatch.setattr(find_tools, "_project_for", lambda ctx: None)
    assert find_tools._allowed_for(_ctx(tmp_path)) == {"file_read"}
    assert seen["called"] == ("a1", "u1")
