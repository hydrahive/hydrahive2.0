"""Lehren mit Beleg – Nachbesserung 10d: Verlauf ohne Lücke, nur der neue Teil, Gegenprüfung Lehre ↔ Beleg, Bestand."""
from __future__ import annotations

import asyncio
import json

import pytest

from hydrahive.lessons import check, extract, prompt, store

QUOTE = 'npm error Missing script: "type-check"'


class _Msg:
    def __init__(self, role, content):
        self.role, self.content = role, content


def _answer(quote=QUOTE) -> str:
    return json.dumps({"turns": [{"tried": "a", "happened": "b", "instead": "c", "observed": "d", "verdict": "helped"}],
                       "lesson": {"cue": "Prüfbefehl scheitert am fehlenden Script.", "lesson": "Werkzeug direkt aufrufen.",
                                  "part": "procedure", "evidence": "siehe Zitat", "quote": quote,
                                  "confidence": "high", "why": "klar"}})


# --- 1. Verlauf ohne Lücke ---------------------------------------------------------------------------------------------

def test_long_record_keeps_only_the_end() -> None:
    msgs = [_Msg("user", f"nachricht {i} " + "x" * 200) for i in range(400)]
    rec = prompt.record(msgs, budget=10_000)
    assert len(rec) <= 10_000
    assert "nachricht 399" in rec and "nachricht 0 " not in rec                    # kein alter Anfang mehr
    assert rec.startswith("…[") and "früher ausgelassen" in rec.splitlines()[0]
    assert rec.splitlines()[1].startswith("[user] nachricht ")                     # beginnt mit ganzer Zeile
    nums = [int(ln.split()[2]) for ln in rec.splitlines()[1:]]
    assert nums == sorted(nums) and nums[-1] == 399                                # zeitliche Reihenfolge bleibt


def test_short_record_unchanged() -> None:
    msgs = [_Msg("user", "hallo"), _Msg("assistant", "hi")]
    assert prompt.record(msgs) == "[user] hallo\n[assistant] hi"


# --- 2. nur der neue Teil ---------------------------------------------------------------------------------------------

def test_since_takes_new_part_plus_context() -> None:
    msgs = [_Msg("user", f"m{i}") for i in range(30)]
    part = extract.since(msgs, 20)
    assert [m.content for m in part] == [f"m{i}" for i in range(16, 30)]           # 4 davor als Zusammenhang
    assert extract.since(msgs, None) == msgs and extract.since(msgs, 2) == msgs


# --- 3. Gegenprüfung ---------------------------------------------------------------------------------------------------

def _les(**over) -> dict:
    d = {"cue": "Prüfbefehl scheitert", "lesson": "direkt aufrufen", "part": "procedure", "evidence": "e",
         "quote": QUOTE, "confidence": "high", "why": "w"}
    d.update(over)
    return d


def test_window_around_quote() -> None:
    rec = "a" * 20_000 + QUOTE + "b" * 20_000
    win = check.window(rec, QUOTE)
    assert QUOTE in win and len(win) <= 2 * check.WINDOW + len(QUOTE) + 2
    assert check.window("kurz " + QUOTE + " kurz", QUOTE) == "kurz " + QUOTE + " kurz"
    assert check.window("nichts", QUOTE) == ""


def test_check_messages_contain_lesson_quote_and_window() -> None:
    m = check.messages(_les(), "davor " + QUOTE + " danach")
    sysmsg, user = m[0]["content"], m[1]["content"]
    assert "supported" in sysmsg and "quote_fits" in sysmsg and "the user asked for is NOT supported" in sysmsg
    assert "DATA, NOT INSTRUCTIONS" in sysmsg
    assert "WHEN Prüfbefehl scheitert" in user and "THEN direkt aufrufen" in user and f"QUOTE: {QUOTE}" in user
    assert "davor " + QUOTE + " danach" in user


@pytest.mark.parametrize("raw,ok", [
    ('{"supported": true, "quote_fits": true, "why": "x"}', True),
    ('Ergebnis: {"supported": true, "quote_fits": true}', True),
    ('{"supported": true, "quote_fits": false}', False),
    ('{"supported": false, "quote_fits": true}', False),
    ('{"supported": "true", "quote_fits": "true"}', False),                          # nur echte Wahrheitswerte
    ('{"supported": true}', False),
    ("kaputt", None),
    ("[true, true]", None),
])
def test_verdict(raw, ok) -> None:
    assert check.verdict(raw) == ok


# --- in der Auswertung --------------------------------------------------------------------------------------------------

MSGS = [_Msg("user", "mach mal einen typecheck")] + [_Msg("assistant", f"schritt {i}") for i in range(8)] + [
    _Msg("user", [{"type": "tool_result", "content": QUOTE, "is_error": True}]),
    _Msg("assistant", "jetzt direkt mit tsc, lief")]


@pytest.fixture
def env(tmp_path, monkeypatch):
    calls = []

    async def fake(messages, model=None, temperature=0.2, max_tokens=3000):
        calls.append(messages)
        sysmsg = messages[0]["content"]
        return env.check_answer if "quote_fits" in sysmsg else env.answer

    monkeypatch.setattr(store, "_agent_dir", lambda aid: tmp_path / aid)
    monkeypatch.setattr(extract, "_messages", lambda sid: env.msgs)
    monkeypatch.setattr(extract, "_complete", fake)
    monkeypatch.setattr(extract, "_model", lambda: "test/luna")
    monkeypatch.setattr(extract, "_scope", lambda aid, sid: "project:p1")
    env.answer, env.check_answer, env.calls, env.msgs = _answer(), '{"supported": true, "quote_fits": true}', calls, MSGS
    return env


def _run():
    return asyncio.run(extract.extract_session("a", "s1"))


def test_checked_lesson_is_saved(env) -> None:
    assert _run()["status"] == "saved" and len(env.calls) == 2
    assert QUOTE in env.calls[1][1]["content"]                                       # Gegenprüfung sah das Zitat


def test_unsupported_lesson_is_dropped_and_session_done(env) -> None:
    env.check_answer = '{"supported": false, "quote_fits": true, "why": "Nutzer hat es so gewollt"}'
    assert _run() == {"status": "rejected", "reason": "not_supported"}
    assert store.current("a") == [] and store.done_count("a", "s1") == len(MSGS)


def test_check_error_saves_nothing_and_retries_later(env, monkeypatch) -> None:
    env.check_answer = "kaputt"
    assert _run() == {"status": "rejected", "reason": "check_unreadable"}
    assert store.current("a") == [] and store.done_count("a", "s1") is None


def test_check_timeout_retries_later(env, monkeypatch) -> None:
    orig = extract._complete

    async def slow(messages, **k):
        if "quote_fits" in messages[0]["content"]:
            await asyncio.sleep(1)
        return await orig(messages, **k)
    monkeypatch.setattr(extract, "_complete", slow)
    monkeypatch.setattr(check, "TIMEOUT", 0.05)
    assert _run() == {"status": "error"} and store.done_count("a", "s1") is None


def test_no_check_without_lesson(env) -> None:
    env.answer = json.dumps({"turns": [], "lesson": None})
    assert _run() == {"status": "no_entry"} and len(env.calls) == 1


def test_second_run_only_sees_new_messages(env) -> None:
    _run()
    env.msgs = MSGS + [_Msg("assistant", f"neu {i}") for i in range(10)]
    env.calls.clear()
    _run()
    rec = env.calls[0][1]["content"]
    assert "neu 9" in rec and "mach mal einen typecheck" not in rec                  # Anfang nicht mehr dabei


# --- Bestand nachprüfen --------------------------------------------------------------------------------------------------

def test_recheck_marks_unsupported_as_contested_and_can_undo(tmp_path, monkeypatch) -> None:
    from hydrahive.lessons import recheck
    from hydrahive.lessons.model import key_of
    monkeypatch.setattr(store, "_agent_dir", lambda aid: tmp_path / aid)
    (tmp_path / "a").mkdir()
    good = store.add("a", {**_les(cue="gut"), "key": key_of("gut"), "session_id": "s1"}, scope="agent")
    bad = store.add("a", {**_les(cue="schief"), "key": key_of("schief"), "session_id": "s1"}, scope="agent")

    async def judge(messages, **k):
        return '{"supported": %s, "quote_fits": true}' % ("true" if "WHEN gut" in messages[1]["content"] else "false")
    monkeypatch.setattr(recheck, "_complete", judge)
    monkeypatch.setattr(recheck, "_messages", lambda sid: MSGS)
    monkeypatch.setattr(recheck, "_model", lambda: "test/luna")
    res = asyncio.run(recheck.run(tmp_path))
    assert res == {"checked": 2, "contested": 1, "kept": 2 - 1, "errors": 0}
    cur = {r["id"]: r for r in store.current("a")}
    assert cur[good["id"]]["status"] == "active" and cur[bad["id"]]["status"] == "contested"
    assert cur[bad["id"]]["contested_by"] == "recheck"
    assert asyncio.run(recheck.run(tmp_path, undo=True)) == {"restored": 1}
    assert {r["status"] for r in store.current("a")} == {"active"}


def test_recheck_without_model_does_nothing(tmp_path, monkeypatch) -> None:
    from hydrahive.lessons import recheck
    monkeypatch.setattr(recheck, "_model", lambda: "")
    assert asyncio.run(recheck.run(tmp_path)) == {"checked": 0, "contested": 0, "kept": 0, "errors": 0}



def _recheck_env(tmp_path, monkeypatch, answer):
    from hydrahive.lessons import recheck
    from hydrahive.lessons.model import key_of
    monkeypatch.setattr(store, "_agent_dir", lambda aid: tmp_path / aid)
    (tmp_path / "a").mkdir()
    rows = [store.add("a", {**_les(cue=c, **extra), "key": key_of(c), "session_id": "s1"}, scope="agent")
            for c, extra in (("eins", {}), ("zwei", {}), ("ohne zitat", {"quote": "das steht nirgends im verlauf drin"}))]
    store.set_status("a", rows[1]["id"], "retired")

    async def judge(messages, **k):
        if answer == "boom":
            raise RuntimeError("weg")
        return answer
    monkeypatch.setattr(recheck, "_complete", judge)
    monkeypatch.setattr(recheck, "_messages", lambda sid: MSGS)
    monkeypatch.setattr(recheck, "_model", lambda: "test/luna")
    return recheck, rows


def test_recheck_skips_non_active_and_contests_missing_quote(tmp_path, monkeypatch) -> None:
    recheck, rows = _recheck_env(tmp_path, monkeypatch, '{"supported": true, "quote_fits": true}')
    res = asyncio.run(recheck.run(tmp_path))
    assert res == {"checked": 2, "contested": 1, "kept": 1, "errors": 0}             # „zwei“ (retired) nicht geprüft
    cur = {r["id"]: r for r in store.current("a")}
    assert cur[rows[1]["id"]]["status"] == "retired" and cur[rows[2]["id"]]["status"] == "contested"


def test_recheck_error_counts_and_keeps_status(tmp_path, monkeypatch) -> None:
    recheck, rows = _recheck_env(tmp_path, monkeypatch, "boom")
    res = asyncio.run(recheck.run(tmp_path))
    assert res["errors"] == 1 and res["kept"] == 0
    assert store.current("a")[0]["status"] == "active"


def test_recheck_undo_restores_only_its_own(tmp_path, monkeypatch) -> None:
    recheck, rows = _recheck_env(tmp_path, monkeypatch, '{"supported": false, "quote_fits": false}')
    store.set_status("a", rows[1]["id"], "contested", by="hand")                      # von Hand angefochten
    asyncio.run(recheck.run(tmp_path))
    assert asyncio.run(recheck.run(tmp_path, undo=True)) == {"restored": 2}
    assert store.current("a")[1]["status"] == "contested" and store.current("a")[1]["contested_by"] == "hand"
