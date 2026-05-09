"""Tests für build_memory_context — Per-Agent-Overrides + Crystal-Scope (#113/#115)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hydrahive.agents._context_injection import build_memory_context
from hydrahive.tools import _crystallize_storage, _memory_io
from hydrahive.tools._crystallize_storage import save_crystal


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    """Crystal- + Memory-Storage je auf eigene Files in tmp_path."""
    crystal_path = tmp_path / "crystals.jsonl"
    memory_path = tmp_path / "memory.json"
    monkeypatch.setattr(_crystallize_storage, "_crystals_file", lambda a: crystal_path)
    monkeypatch.setattr(_memory_io, "_memory_file", lambda a: memory_path)
    return crystal_path, memory_path


def _crystal(sid: str, *, project: str | None = None, narrative: str = "n") -> dict:
    return {
        "id": f"cry-{sid}",
        "session_id": sid,
        "agent_id": "a",
        "project": project,
        "created_at": "2026-05-09T00:00:00Z",
        "narrative": narrative,
        "key_outcomes": [],
        "files_affected": [],
        "lessons": [],
        "source_observation_ids": [],
        "observation_count": 0,
    }


def _seed_lesson(memory_path: Path, key: str, content: str, *, confidence: float = 0.7,
                 project: str | None = None) -> None:
    data = {}
    if memory_path.exists():
        data = json.loads(memory_path.read_text())
    data[key] = {
        "content": content,
        "created_at": "2026-05-09T00:00:00Z",
        "updated_at": "2026-05-09T00:00:00Z",
        "expires_at": None,
        "confidence": confidence,
        "reinforcements": 0,
        "last_reinforced_at": None,
        "is_latest": True,
        "superseded_by": None,
        "superseded_at": None,
        "supersedes": [],
        "project": project,
    }
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text(json.dumps(data))


# --- Defaults: build_memory_context ohne agent_config -------------------

def test_keine_daten_returns_none(isolated_storage):
    assert build_memory_context("a") is None


def test_default_zeigt_crystal_und_lesson(isolated_storage):
    crystal_path, memory_path = isolated_storage
    save_crystal("a", _crystal("s1", narrative="hello"))
    _seed_lesson(memory_path, "lesson.x", "be kind")
    result = build_memory_context("a")
    assert result is not None
    assert "hello" in result
    assert "be kind" in result


# --- #115: Per-Agent-Override ------------------------------------------

def test_max_crystals_zero_versteckt_crystals(isolated_storage):
    save_crystal("a", _crystal("s1", narrative="hidden"))
    result = build_memory_context("a", agent_config={"memory_max_crystals": 0})
    assert result is None or "hidden" not in result


def test_max_lessons_zero_versteckt_lessons(isolated_storage):
    _, memory_path = isolated_storage
    _seed_lesson(memory_path, "lesson.x", "hidden lesson")
    result = build_memory_context("a", agent_config={"memory_max_lessons": 0})
    assert result is None or "hidden lesson" not in result


def test_alles_null_returns_none(isolated_storage):
    save_crystal("a", _crystal("s1"))
    _, memory_path = isolated_storage
    _seed_lesson(memory_path, "lesson.x", "x")
    result = build_memory_context("a", agent_config={
        "memory_max_crystals": 0,
        "memory_max_lessons": 0,
    })
    assert result is None


def test_min_confidence_threshold_filtert(isolated_storage):
    _, memory_path = isolated_storage
    _seed_lesson(memory_path, "lesson.low", "low conf", confidence=0.5)
    _seed_lesson(memory_path, "lesson.high", "high conf", confidence=0.9)
    result = build_memory_context("a", agent_config={
        "memory_min_lesson_confidence": 0.8,
    })
    assert result is not None
    assert "high conf" in result
    assert "low conf" not in result


def test_max_chars_kuerzt_block(isolated_storage):
    _, memory_path = isolated_storage
    for i in range(20):
        _seed_lesson(memory_path, f"lesson.{i}", "x" * 100)
    result = build_memory_context("a", agent_config={
        "memory_max_chars": 200,
        "memory_max_lessons": 50,
    })
    assert result is not None
    assert "truncated" in result
    # Block plus Truncation-Hinweis ist akzeptabel; harter Soft-Cap nicht
    # zwingend bei 200, aber massiv kürzer als ohne Limit:
    assert len(result) < 500


def test_max_lessons_limit(isolated_storage):
    _, memory_path = isolated_storage
    for i in range(20):
        _seed_lesson(memory_path, f"lesson.{i}", f"lesson #{i}", confidence=0.7)
    result = build_memory_context("a", agent_config={"memory_max_lessons": 3})
    assert result is not None
    lesson_count = result.count("\n- lesson #")
    assert lesson_count == 3


# --- #113: Crystal-Scope ----------------------------------------------

def test_crystal_scope_default_project_and_global(isolated_storage):
    save_crystal("a", _crystal("s1", project="p1", narrative="own"))
    save_crystal("a", _crystal("s2", project=None, narrative="globally"))
    result = build_memory_context("a", project_id="p1")
    assert result is not None
    assert "own" in result
    assert "globally" in result  # Default = sieht global


def test_crystal_scope_project_only_isoliert(isolated_storage):
    save_crystal("a", _crystal("s1", project="p1", narrative="own"))
    save_crystal("a", _crystal("s2", project=None, narrative="globally"))
    result = build_memory_context("a", project_id="p1", agent_config={
        "memory_crystal_scope": "project_only",
    })
    assert result is not None
    assert "own" in result
    assert "globally" not in result


def test_crystal_scope_andere_projekte_unsichtbar(isolated_storage):
    """Auch im project_and_global-Modus dürfen Crystals fremder Projekte nicht durchsickern."""
    save_crystal("a", _crystal("s1", project="p2", narrative="other-project"))
    save_crystal("a", _crystal("s2", project=None, narrative="globally"))
    result = build_memory_context("a", project_id="p1")
    if result is None:
        return  # OK — nur Global ohne weitere Inhalte ist akzeptabel
    assert "other-project" not in result


def test_crystal_scope_kein_project_id_zeigt_alle(isolated_storage):
    """Master-Agent ohne Projekt sieht alle Crystals (Filter inaktiv)."""
    save_crystal("a", _crystal("s1", project="p1", narrative="p1-stuff"))
    save_crystal("a", _crystal("s2", project=None, narrative="globally"))
    result = build_memory_context("a")
    assert result is not None
    assert "p1-stuff" in result
    assert "globally" in result
