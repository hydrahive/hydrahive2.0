"""Projekt-Skills folgen dem Projekt der Session, nicht nur agent.project_id (MED-2).

Buddy/Master mit gewähltem Projekt sollen die geteilte Projekt-Bibliothek sehen,
wie es write_skill verspricht ("alle Agenten deines Projekts sehen ihn").
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from hydrahive.skills.loader import save_skill
from hydrahive.skills.models import Skill
from hydrahive.tools.base import ToolContext


def _skill(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path, raising=False)
    save_skill(Skill(name="proj-regel", description="d", when_to_use="w", body="Projekt-Body",
                     scope="project", owner="proj-1"))


def _agent(monkeypatch, project_id=None):
    monkeypatch.setattr("hydrahive.agents.config.get", lambda _id: {
        "id": "buddy-1", "owner": "u", "disabled_skills": [], "project_id": project_id})


def _ctx(project_id):
    return ToolContext(session_id="s", agent_id="buddy-1", user_id="u", workspace=Path("/tmp"),
                       project_id=project_id)


def test_list_skills_sieht_projekt_skills_der_session(tmp_path, monkeypatch):
    from hydrahive.tools import list_skills
    _skill(tmp_path, monkeypatch)
    _agent(monkeypatch)
    res = asyncio.run(list_skills.TOOL.execute({}, _ctx("proj-1")))
    assert "proj-regel" in [s["name"] for s in res.output["skills"]]


def test_list_skills_ohne_projekt_keine_projekt_skills(tmp_path, monkeypatch):
    from hydrahive.tools import list_skills
    _skill(tmp_path, monkeypatch)
    _agent(monkeypatch)
    res = asyncio.run(list_skills.TOOL.execute({}, _ctx(None)))
    assert "proj-regel" not in [s["name"] for s in res.output["skills"]]


def test_load_skill_laedt_projekt_skill_der_session(tmp_path, monkeypatch):
    from hydrahive.tools import load_skill
    _skill(tmp_path, monkeypatch)
    _agent(monkeypatch)
    res = asyncio.run(load_skill.TOOL.execute({"name": "proj-regel"}, _ctx("proj-1")))
    assert res.success and res.output["body"] == "Projekt-Body"


def test_projekt_agent_ohne_session_projekt_behaelt_seine_skills(tmp_path, monkeypatch):
    from hydrahive.tools import list_skills
    _skill(tmp_path, monkeypatch)
    _agent(monkeypatch, project_id="proj-1")
    res = asyncio.run(list_skills.TOOL.execute({}, _ctx(None)))
    assert "proj-regel" in [s["name"] for s in res.output["skills"]]


def test_runner_nutzt_session_projekt_fuer_skills():
    src = (Path(__file__).parents[1] / "src/hydrahive/runner/runner.py").read_text(encoding="utf-8")
    assert "project_id=skill_project_id(active_project_id, agent)" in src
