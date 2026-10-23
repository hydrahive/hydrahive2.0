"""Hilfe-Assistent: Werkzeuge help_search / help_read (docs/plans/help-assistant.md, Etappe 1, Schritt 2)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.helpdesk import _manual as manual
from hydrahive.tools import help_read, help_search
from hydrahive.tools.base import ToolContext


@pytest.fixture
def repo(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / "frontend" / "src" / "i18n" / "help" / "de"
    d.mkdir(parents=True)
    (d / "agents.md").write_text("# Agenten\n\n## Neuen Agent anlegen\n\nKlicke auf „Neuer Agent“.\n")
    (d / "lang.md").write_text("# Lang\n\n" + ("Satz. " * 5000))
    (tmp_path / "frontend" / "src" / "i18n" / "help" / "en").mkdir()
    (tmp_path / "frontend" / "src" / "i18n" / "help" / "en" / "agents.md").write_text("# Agents\n\nEnglish.\n")
    monkeypatch.setattr(manual, "REPO_ROOT", tmp_path)
    manual.clear_cache()
    return tmp_path


def _ctx(lang: str = "de") -> ToolContext:
    return ToolContext(session_id="s", agent_id="a", user_id="u", workspace=Path("/tmp"), config={"help_lang": lang})


def _run(tool, args: dict, lang: str = "de"):
    return asyncio.run(tool.TOOL.execute(args, _ctx(lang)))


def test_search_returns_hits(repo):
    r = _run(help_search, {"query": "Agent anlegen"})
    assert r.success
    assert r.output["hits"][0] == {"topic": "agents", "heading": "Neuen Agent anlegen",
                                   "excerpt": "Klicke auf „Neuer Agent“."}


def test_search_no_hits_lists_topics(repo):
    """Kein Treffer → Liste der Themen, damit der Agent mit help_read weitermachen kann statt zu raten."""
    r = _run(help_search, {"query": "xyzunbekannt"})
    assert r.success and r.output["hits"] == []
    assert r.output["topics"] == ["agents", "lang"]


def test_search_requires_query(repo):
    assert not _run(help_search, {}).success
    assert not _run(help_search, {"query": "  "}).success


def test_read_uses_user_language(repo):
    assert _run(help_read, {"topic": "agents"}, lang="en").output["text"].startswith("# Agents")
    assert _run(help_read, {"topic": "agents"}, lang="de").output["text"].startswith("# Agenten")


def test_read_unknown_topic_fails_with_topics(repo):
    r = _run(help_read, {"topic": "../../etc/passwd"})
    assert not r.success
    assert "agents" in r.error


def test_read_long_article_is_cut(repo):
    r = _run(help_read, {"topic": "lang"})
    assert r.success
    assert len(r.output["text"]) <= help_read.MAX_CHARS
    assert r.output["truncated"] is True


def test_tools_are_read_only_category():
    assert help_search.TOOL.category == help_read.TOOL.category == "help"


def test_tools_registered():
    from hydrahive.tools import REGISTRY
    assert "help_search" in REGISTRY and "help_read" in REGISTRY


def test_tools_import_in_fresh_process():
    """Import-Kreis tools → help_search → helpdesk → agents → tools darf nicht entstehen (Befund 23.10.2026)."""
    import os
    import subprocess
    import sys
    src = str(Path(__file__).resolve().parents[1] / "src")      # dieser Stand, nicht eine installierte Kopie
    env = {**os.environ, "PYTHONPATH": src}
    for mod in ("hydrahive.tools", "hydrahive.helpdesk._agent", "hydrahive.api.routes.agents"):
        r = subprocess.run([sys.executable, "-c", f"import {mod}"], capture_output=True, text=True, timeout=60,
                           env=env)
        assert r.returncode == 0, mod + r.stderr[-500:]
