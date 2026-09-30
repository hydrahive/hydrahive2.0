"""stop_reason "refusal": klare Meldung + errors_log (Task 891f1d3a, Teil a).

Belegt 27.09.2026 (Session 01a09709): Zwei Läufe endeten mit refusal, die
Antwort enthielt nur einen thinking-Block. Seit Juni gab es 15 refusals, 3 davon
mit Text oder Tool-Aufrufen. Bisher:
- ohne Text: generische Meldung „leere Antwort“, kein errors_log-Eintrag
- mit Text: der Lauf galt als „completed“ oder lief mit Tools weiter,
  ohne Hinweis auf den Abbruch
Jetzt beendet refusal den Lauf immer mit eigener Meldung (kind="refusal"),
schließt offene Tool-Aufrufe und schreibt errors_log.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.db import errors_log, init_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import runner as runner_mod
from hydrahive.runner._runner_iter import IterationResult
from hydrahive.runner.events import Done, Error
from hydrahive.tools._sessions import session_get
from tests._own_rows import only_own_rows

AGENT_ID = "test-agent-001"

THINKING = {"type": "thinking", "thinking": "…", "signature": "sig"}
TEXT = {"type": "text", "text": "Ich prüfe zuerst die Dateien."}
TOOL = {"type": "tool_use", "id": "toolu_r1", "name": "shell_exec", "input": {"cmd": "ls"}}


@pytest.fixture(autouse=True)
def _own_errors(setup_test_env):
    init_db()                      # errors_log muss existieren, bevor wir sie merken
    with only_own_rows("errors_log"):
        yield


def _session() -> str:
    init_db()
    return sessions_db.create(agent_id=AGENT_ID, user_id="admin", title="refusal-test").id


def _stream(monkeypatch, blocks: list[dict], stop: str = "refusal") -> list:
    calls: list[str] = []

    async def fake_stream(**kwargs):
        yield IterationResult(
            blocks=blocks, stop_reason=stop, used_model=kwargs["primary_model"],
            input_tokens=10, output_tokens=5, cache_creation_tokens=0, cache_read_tokens=0,
        )

    async def fake_process(tool_uses, **kwargs):
        calls.append("tools")
        yield [{"type": "tool_result", "tool_use_id": tu["id"], "content": "ok"} for tu in tool_uses]

    monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)
    monkeypatch.setattr(runner_mod, "process_tool_uses", fake_process)
    monkeypatch.setattr(runner_mod, "should_compact", lambda *a, **k: False)
    return calls


def _run(sid: str) -> list:
    async def drain():
        return [e async for e in runner_mod.run(sid, "mach was")]
    return asyncio.run(drain())


def _errors(events) -> list[Error]:
    return [e for e in events if isinstance(e, Error)]


@pytest.mark.parametrize("blocks", [[THINKING], [THINKING, TEXT], [TEXT, TOOL]],
                         ids=["nur_thinking", "mit_text", "mit_tool"])
def test_refusal_ends_run_with_own_message(monkeypatch, blocks):
    sid = _session()
    tool_calls = _stream(monkeypatch, blocks)
    events = _run(sid)
    errs = _errors(events)
    assert len(errs) == 1, events
    assert errs[0].metadata.get("kind") == "refusal"
    assert "abgelehnt" in errs[0].message or "refusal" in errs[0].message
    assert not any(isinstance(e, Done) for e in events)
    assert tool_calls == []                     # angefangene Tools laufen NICHT
    assert session_get(AGENT_ID, sid)["status"] == "abandoned"


def test_refusal_is_logged(monkeypatch):
    sid = _session()
    _stream(monkeypatch, [THINKING])
    _run(sid)
    rows = errors_log.for_session(sid)
    assert any(r["source"] == "runner.refusal" for r in rows), rows


def test_refusal_closes_open_tool_uses(monkeypatch):
    """Ein abgebrochener tool_use braucht ein tool_result, sonst lehnt das
    nächste LLM-Call die History ab."""
    from hydrahive.db import messages as messages_db
    sid = _session()
    _stream(monkeypatch, [TEXT, TOOL])
    _run(sid)
    history = messages_db.list_for_llm(sid)
    results = [b for m in history if m.role == "user" and isinstance(m.content, list)
               for b in m.content if isinstance(b, dict) and b.get("type") == "tool_result"]
    assert any(b.get("tool_use_id") == "toolu_r1" for b in results)


def test_normal_end_turn_is_unchanged(monkeypatch):
    sid = _session()
    _stream(monkeypatch, [TEXT], stop="end_turn")
    events = _run(sid)
    assert _errors(events) == []
    assert any(isinstance(e, Done) for e in events)


def test_empty_answer_without_refusal_keeps_generic_message(monkeypatch):
    sid = _session()
    _stream(monkeypatch, [THINKING], stop="end_turn")
    errs = _errors(_run(sid))
    assert len(errs) == 1 and errs[0].metadata.get("kind") != "refusal"
    assert "leere Antwort" in errs[0].message
