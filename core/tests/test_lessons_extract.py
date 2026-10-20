"""Lehren mit Beleg L1: eine Sitzung auswerten (Modell ersetzt), alte Lehren abschalten, Bestand markieren."""
from __future__ import annotations

import asyncio
import json

import pytest

from hydrahive.lessons import extract, store

QUOTE = 'npm error Missing script: "type-check"'


class _Msg:
    def __init__(self, role, content):
        self.role, self.content = role, content


MSGS = [_Msg("user", "mach mal einen typecheck")] + [_Msg("assistant", f"schritt {i}") for i in range(8)] + [
    _Msg("user", [{"type": "tool_result", "content": QUOTE, "is_error": True}]),
    _Msg("assistant", "jetzt direkt mit tsc, lief")]


def _answer(quote=QUOTE) -> str:
    return json.dumps({"turns": [{"tried": "a", "happened": "b", "instead": "c", "observed": "d", "verdict": "helped"}],
                       "lesson": {"cue": "Prüfbefehl scheitert am fehlenden Script.", "lesson": "Werkzeug direkt aufrufen.",
                                  "part": "procedure", "evidence": "siehe Zitat", "quote": quote,
                                  "confidence": "high", "why": "klar"}})


@pytest.fixture
def env(tmp_path, monkeypatch):
    calls = []

    async def fake_complete(messages, model=None, temperature=0.7, max_tokens=4096):
        calls.append({"model": model, "messages": messages})
        return env.answer

    monkeypatch.setattr(store, "_agent_dir", lambda aid: tmp_path / aid)
    monkeypatch.setattr(extract, "_messages", lambda sid: MSGS)
    monkeypatch.setattr(extract, "_complete", fake_complete)
    monkeypatch.setattr(extract, "_model", lambda: "test/luna")
    monkeypatch.setattr(extract, "_scope", lambda aid, sid: "project:p1")
    env.answer, env.calls, env.dir = _answer(), calls, tmp_path
    return env


def _run(aid="a", sid="s1"):
    return asyncio.run(extract.extract_session(aid, sid))


def test_session_gives_one_lesson(env) -> None:
    res = _run()
    assert res["status"] == "saved" and res["lesson"]["scope"] == "project:p1"
    assert env.calls[0]["model"] == "test/luna" and "DATA, NOT INSTRUCTIONS" in env.calls[0]["messages"][0]["content"]
    assert len(store.current("a")) == 1 and store.is_done("a", "s1")


def test_done_session_is_skipped(env) -> None:
    _run()
    assert _run()["status"] == "skipped_done" and len(env.calls) == 1


def test_short_session_is_skipped(env, monkeypatch) -> None:
    monkeypatch.setattr(extract, "_messages", lambda sid: MSGS[:9])
    assert _run()["status"] == "skipped_short" and env.calls == [] and not store.is_done("a", "s1")


def test_model_off_does_nothing(env, monkeypatch) -> None:
    monkeypatch.setattr(extract, "_model", lambda: "")
    assert _run()["status"] == "off" and env.calls == []


def test_quote_not_in_record_saves_nothing_but_marks_done(env) -> None:
    env.answer = _answer(quote="das steht nirgends im Verlauf drin")
    res = _run()
    assert res == {"status": "rejected", "reason": "quote_not_found"}
    assert store.current("a") == [] and store.is_done("a", "s1")


def test_no_entry_marks_done(env) -> None:
    env.answer = json.dumps({"turns": [], "lesson": None})
    assert _run() == {"status": "no_entry"} and store.is_done("a", "s1")


def test_unreadable_answer_is_not_marked_done(env) -> None:
    env.answer = "leider nein"
    assert _run() == {"status": "rejected", "reason": "unreadable"}
    assert not store.is_done("a", "s1")                                              # nächstes Mal neu versuchen


def test_llm_error_is_not_marked_done(env, monkeypatch) -> None:
    async def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(extract, "_complete", boom)
    assert _run() == {"status": "error"} and not store.is_done("a", "s1")


# --- alte Lehren der Zusammenfassung abschalten ----------------------------------------------------------------------

def test_crystallize_saves_old_lessons_only_when_switched_on(monkeypatch) -> None:
    from hydrahive.llm import _config
    from hydrahive.tools import _crystallize, _memory_store
    written = []
    monkeypatch.setattr(_memory_store, "write_keys_bulk", lambda aid, entries: written.extend(entries))
    monkeypatch.setattr(_config, "load_config", lambda: {})
    assert _crystallize._save_lessons("a", ["Read files first"], None) == [] and written == []
    monkeypatch.setattr(_config, "load_config", lambda: {"legacy_lessons": True})
    assert len(_crystallize._save_lessons("a", ["Read files first"], None)) == 1 and len(written) == 1


# --- Bestand markieren -------------------------------------------------------------------------------------------------

def test_mark_legacy_marks_only_hash_lessons_and_can_undo(tmp_path) -> None:
    from hydrahive.lessons import mark_legacy
    mem = tmp_path / "a1" / "memory.json"
    mem.parent.mkdir()
    data = {"lesson.0123456789ab": {"content": "auto"}, "lesson.kern-suite-tmpdir": {"content": "hand"},
            "notiz": {"content": "x"}}
    mem.write_text(json.dumps(data))
    assert mark_legacy.run(tmp_path) == {"files": 1, "marked": 1}
    got = json.loads(mem.read_text())
    assert got["lesson.0123456789ab"]["legacy_lesson"] is True
    assert "legacy_lesson" not in got["lesson.kern-suite-tmpdir"] and "legacy_lesson" not in got["notiz"]
    assert mark_legacy.run(tmp_path) == {"files": 1, "marked": 0}                    # zweimal = gleich
    assert mark_legacy.run(tmp_path, undo=True) == {"files": 1, "marked": 1}
    assert "legacy_lesson" not in json.loads(mem.read_text())["lesson.0123456789ab"]


# --- Runner stößt die Auswertung im Hintergrund an ---------------------------------------------------------------------

def test_runner_starts_lessons_in_background(monkeypatch) -> None:
    from hydrahive.lessons import extract as ex
    from hydrahive.runner import _runner_lessons
    seen = []

    async def fake(aid, sid):
        seen.append((aid, sid))
        raise RuntimeError("darf den Runner nicht stören")

    monkeypatch.setattr(ex, "extract_session", fake)

    async def go():
        await _runner_lessons.start_lessons("a", "s1")
    asyncio.run(go())
    assert seen == [("a", "s1")]


def test_runner_calls_start_lessons_after_completed_turn() -> None:
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "src/hydrahive/runner/runner.py").read_text()
    end = src.index('session_end(agent["id"], session_id, status="completed")')
    done = src.index("yield Done(", end)
    assert 'start_lessons(agent["id"], session_id)' in src[end:done]
