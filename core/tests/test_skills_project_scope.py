"""Tests für den project-Skill-Scope (geteilte Projekt-Bibliothek)."""
from __future__ import annotations

from hydrahive.skills.loader import get_skill, list_for_agent, save_skill
from hydrahive.skills.models import Skill
from hydrahive.skills._paths import dir_for


def test_project_scope_dir(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path, raising=False)
    assert dir_for("project", "proj-1") == tmp_path / "projects" / "proj-1" / "skills"


def test_project_skill_roundtrip(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path, raising=False)
    ok, _ = save_skill(Skill(
        name="rust-review", description="d", when_to_use="w", body="b",
        scope="project", owner="proj-1",
    ))
    assert ok
    s = get_skill("project", "proj-1", "rust-review")
    assert s and s.name == "rust-review" and s.scope == "project"


def test_list_for_agent_includes_project_skills(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path, raising=False)
    save_skill(Skill(name="shared", description="d", when_to_use="w", body="b",
                     scope="project", owner="proj-1"))
    with_proj = [s.name for s in list_for_agent("ag-1", "owner-1", project_id="proj-1")]
    without = [s.name for s in list_for_agent("ag-1", "owner-1")]
    assert "shared" in with_proj
    assert "shared" not in without
