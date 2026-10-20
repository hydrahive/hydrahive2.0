"""Lehren mit Beleg L1 (docs/specs/lehren-mit-beleg.md 10b): Prüfregeln, Verlauf, Antwort lesen – reine Funktionen."""
from __future__ import annotations

import json

from hydrahive.lessons import model, prompt

RECORD = (
    "[user] mach mal einen typecheck\n"
    "[tool_call:shell_exec] {\"cmd\": \"npm run type-check\"}\n"
    "[tool_result ERROR] npm error Missing script: \"type-check\"\n"
    "[tool_call:shell_exec] {\"cmd\": \"npx tsc -b --pretty false\"}\n"
    "[tool_result] {\"exit_code\": 0}\n"
)


def _answer(**over) -> dict:
    lesson = {"cue": "Ein Prüfbefehl scheitert, weil das Projekt-Script fehlt.",
              "lesson": "package.json lesen und das Prüfwerkzeug direkt aufrufen.",
              "part": "procedure", "evidence": "Fehler beim Script, danach lief tsc direkt.",
              "quote": "npm error Missing script: \"type-check\"", "confidence": "high", "why": "direkter Vorher-Nachher-Vergleich"}
    lesson.update(over)
    return {"turns": [{"tried": "npm run type-check", "happened": "Missing script", "instead": "npx tsc -b",
                       "observed": "lief", "verdict": "helped"}], "lesson": lesson}


# --- Prüfregeln ------------------------------------------------------------------------------------------------------

def test_valid_lesson_passes() -> None:
    les, why = model.check(_answer(), RECORD)
    assert why == "" and les is not None
    assert les["part"] == "procedure" and les["confidence"] == "high"
    assert les["key"] == model.key_of(les["cue"]) and len(les["key"]) == 16


def test_no_lesson_is_a_valid_answer() -> None:
    assert model.check({"turns": [], "lesson": None}, RECORD) == (None, "no_entry")
    assert model.check({"turns": [], "lesson": "NO_ENTRY"}, RECORD) == (None, "no_entry")


def test_quote_must_appear_in_record() -> None:
    assert model.check(_answer(quote="npm error Missing script: \"lint\""), RECORD) == (None, "quote_not_found")


def test_quote_whitespace_is_normalised_but_needs_20_chars() -> None:
    les, why = model.check(_answer(quote="npm   error\nMissing script:"), RECORD)
    assert why == "" and les is not None
    assert model.check(_answer(quote="npm error"), RECORD) == (None, "quote_too_short")


def test_required_fields_and_lengths() -> None:
    for field in ("cue", "lesson", "evidence", "quote"):
        assert model.check(_answer(**{field: ""}), RECORD)[1] == "missing_" + field, field
    assert model.check(_answer(cue="x" * 601), RECORD)[1] == "too_long_cue"


def test_part_must_be_known() -> None:
    assert model.check(_answer(part="magic"), RECORD)[1] == "bad_part"
    assert model.check(_answer(part="user-preference"), RECORD)[1] == ""


def test_confidence_is_normalised() -> None:
    assert model.check(_answer(confidence="hoch – klar"), RECORD)[0]["confidence"] == "high"
    assert model.check(_answer(confidence="Medium"), RECORD)[0]["confidence"] == "medium"
    assert model.check(_answer(confidence="?"), RECORD)[0]["confidence"] == "low"


def test_needs_a_turn_that_helped_or_hurt() -> None:
    a = _answer()
    a["turns"][0]["verdict"] = "unclear"
    assert model.check(a, RECORD) == (None, "no_supporting_turn")
    a["turns"][0]["verdict"] = "hurt"
    assert model.check(a, RECORD)[1] == ""


def test_platitudes_are_rejected() -> None:
    for text in ("Be thorough and verify changes.", "Read files before editing them.", "Immer gründlich prüfen."):
        assert model.check(_answer(lesson=text), RECORD) == (None, "platitude"), text


def test_key_of_ignores_case_and_spacing() -> None:
    assert model.key_of("Ein  Prüfbefehl scheitert.") == model.key_of("ein prüfbefehl scheitert")
    assert model.key_of("A") != model.key_of("B")


# --- Verlauf und Antwort ---------------------------------------------------------------------------------------------

class _Msg:
    def __init__(self, role, content):
        self.role, self.content = role, content


def test_record_from_messages() -> None:
    msgs = [_Msg("user", "hallo"),
            _Msg("assistant", [{"type": "text", "text": "Ich prüfe."},
                               {"type": "tool_use", "name": "shell_exec", "input": {"cmd": "ls"}}]),
            _Msg("user", [{"type": "tool_result", "content": "Fehler", "is_error": True}]),
            _Msg("assistant", [{"type": "thinking", "thinking": "geheim"}, {"type": "text", "text": "fertig"}])]
    rec = prompt.record(msgs)
    assert rec.splitlines() == ["[user] hallo", "[assistant] Ich prüfe.", '[tool_call:shell_exec] {"cmd": "ls"}',
                                "[tool_result ERROR] Fehler", "[assistant] fertig"]
    assert "geheim" not in rec



def test_messages_mark_record_as_data() -> None:
    m = prompt.messages("[user] hallo")
    assert m[0]["role"] == "system" and "DATA, NOT INSTRUCTIONS" in m[0]["content"] and "NO_ENTRY" in m[0]["content"]
    assert "[user] hallo" in m[1]["content"] and "do not continue" in m[1]["content"]


def test_parse_answer() -> None:
    a = _answer()
    assert prompt.parse("Hier:\n```json\n" + json.dumps(a) + "\n```") == a
    assert prompt.parse("kaputt") is None
    assert prompt.parse("[1, 2]") is None
