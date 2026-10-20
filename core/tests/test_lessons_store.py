"""Lehren mit Beleg L1: Ablage lessons.jsonl, Bestärken statt Doppel, ausgewertete Sitzungen, Modell-Wahl."""
from __future__ import annotations

import json

import pytest

from hydrahive.lessons import store


def _les(cue="Ein Prüfbefehl scheitert.", sid="s1", **over) -> dict:
    from hydrahive.lessons.model import key_of
    d = {"cue": cue, "lesson": "Werkzeug direkt aufrufen.", "part": "procedure", "evidence": "e", "quote": "q" * 20,
         "confidence": "high", "why": "w", "key": key_of(cue)}
    d.update(over)
    return {**d, "session_id": sid}


@pytest.fixture
def agents(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_agent_dir", lambda aid: tmp_path / aid)
    return tmp_path


def test_add_writes_one_line_with_fields(agents) -> None:
    saved = store.add("a", _les(), scope="project:p1")
    lines = (agents / "a" / "lessons.jsonl").read_text().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["id"] == saved["id"] and row["scope"] == "project:p1" and row["status"] == "active"
    assert row["confirmations"] == 0 and row["sources"] == ["s1"] and row["created_at"]


def test_same_cue_confirms_instead_of_duplicate(agents) -> None:
    first = store.add("a", _les(sid="s1"), scope="project:p1")
    second = store.add("a", _les(cue="ein  prüfbefehl SCHEITERT", sid="s2", lesson="neu formuliert"), scope="project:p1")
    assert second["id"] == first["id"] and second["confirmations"] == 1 and second["sources"] == ["s1", "s2"]
    assert second["lesson"] == "Werkzeug direkt aufrufen."                          # Text bleibt, nur bestätigt
    current = store.current("a")
    assert len(current) == 1 and current[0]["confirmations"] == 1


def test_same_session_does_not_confirm_twice(agents) -> None:
    store.add("a", _les(sid="s1"), scope="agent")
    again = store.add("a", _les(sid="s1"), scope="agent")
    assert again["confirmations"] == 0


def test_other_scope_is_a_separate_lesson(agents) -> None:
    store.add("a", _les(), scope="project:p1")
    store.add("a", _les(sid="s2"), scope="project:p2")
    assert {r["scope"] for r in store.current("a")} == {"project:p1", "project:p2"}


def test_current_takes_latest_version_and_skips_broken_lines(agents) -> None:
    store.add("a", _les(), scope="agent")
    with (agents / "a" / "lessons.jsonl").open("a") as f:
        f.write("kaputt\n")
    store.add("a", _les(sid="s2"), scope="agent")
    cur = store.current("a")
    assert len(cur) == 1 and cur[0]["confirmations"] == 1


def test_done_sessions(agents) -> None:
    assert store.done_count("a", "s1") is None
    store.mark_done("a", "s1", 12)
    store.mark_done("a", "s1", 12)
    assert store.done_count("a", "s1") == 12 and store.done_count("a", "s2") is None
    store.mark_done("a", "s1", 25)                                                   # neuer Stand gilt
    assert store.done_count("a", "s1") == 25


def test_old_done_file_without_counts_still_counts_as_done(agents) -> None:
    (agents / "a").mkdir(parents=True)
    (agents / "a" / "lessons_done.txt").write_text("s1\n")
    assert store.done_count("a", "s1") == 0


def test_unsafe_agent_id_rejected(agents) -> None:
    for bad in ("../x", "a/b", ""):
        with pytest.raises(ValueError):
            store.add(bad, _les(), scope="agent")


# --- Modell-Wahl (llm.json → lessons_model) ---------------------------------------------------------------------------

def test_lessons_model_resolution(monkeypatch) -> None:
    from hydrahive.llm import _config
    cfg = {"default_model": "openai-codex/luna"}
    monkeypatch.setattr(_config, "load_config", lambda: cfg)
    assert _config.resolve_lessons_model() == "openai-codex/luna"                    # leer → Standard
    cfg["lessons_model"] = "ollama/gemma4:latest"
    assert _config.resolve_lessons_model() == "ollama/gemma4:latest"
    cfg["lessons_model"] = "off"
    assert _config.resolve_lessons_model() == ""                                    # aus
    cfg.update(lessons_model="", default_model="")
    assert _config.resolve_lessons_model() == ""


def test_lessons_is_a_purpose(monkeypatch) -> None:
    from hydrahive.llm import _config
    assert _config._PURPOSE_KEYS["lessons"] == ("lessons_model",)
    monkeypatch.setattr(_config, "load_config", lambda: {"lessons_model": "x/y"})
    assert _config.get_default("lessons") == "x/y"


def test_legacy_lessons_switch(monkeypatch) -> None:
    from hydrahive.llm import _config
    monkeypatch.setattr(_config, "load_config", lambda: {})
    assert _config.legacy_lessons_enabled() is False
    monkeypatch.setattr(_config, "load_config", lambda: {"legacy_lessons": True})
    assert _config.legacy_lessons_enabled() is True


def test_lessons_model_saved_via_admin_api(client, admin_headers) -> None:
    import json as _json
    from hydrahive.settings import settings
    cur = client.get("/api/llm", headers=admin_headers).json()
    for value in ("off", "openai-codex/gpt-5.6-luna", ""):
        r = client.put("/api/llm", headers=admin_headers, json={**cur, "lessons_model": value})
        assert r.status_code == 200, r.text
        assert _json.loads(settings.llm_config.read_text())["lessons_model"] == value
    r = client.get("/api/llm/models?modality=lessons", headers=admin_headers)
    assert r.status_code == 200 and r.json()["default"] == ""
