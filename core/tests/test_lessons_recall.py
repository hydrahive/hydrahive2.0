"""Lehren mit Beleg L2 (docs/specs/lehren-mit-beleg.md 10c): passende Lehren vor der Arbeit zeigen."""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.lessons import recall, store
from hydrahive.lessons.model import key_of


def _les(cue, lesson="tu das", scope="project:p1", sid="s1", **over) -> dict:
    d = {"cue": cue, "lesson": lesson, "part": "procedure", "evidence": "e", "quote": "q" * 20,
         "confidence": "high", "why": "w", "key": key_of(cue), "session_id": sid}
    d.update(over)
    return store.add("a", d, scope=scope)


@pytest.fixture
def agents(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_agent_dir", lambda aid: tmp_path / aid)
    return tmp_path


class FakeEmbed:
    """Vektor = Wörter als Achsen – gleiche Wörter → ähnlich. Zählt Aufrufe."""
    AXES = ("datei", "script", "chat", "hängt", "bild", "wetter", "login")

    def __init__(self):
        self.calls = []

    async def __call__(self, texts, model, embed_type="db"):
        self.calls.append((tuple(texts), embed_type))
        return [[float(a in t.lower()) for a in self.AXES] for t in texts]


@pytest.fixture
def emb(monkeypatch):
    fake = FakeEmbed()
    monkeypatch.setattr(recall, "_embed", fake)
    monkeypatch.setattr(recall, "_embed_model", lambda: "test/emb")
    return fake


def _pick(text, project="p1"):
    return asyncio.run(recall.pick("a", text, project_id=project))


# --- Auswahl ---------------------------------------------------------------------------------------------------------

def test_matching_lesson_is_picked(agents, emb) -> None:
    _les("Wenn eine Datei fehlt")
    _les("Wenn der Chat hängt", sid="s2")
    got = _pick("die datei finde ich nicht")
    assert [g["cue"] for g in got] == ["Wenn eine Datei fehlt"]
    assert got[0]["similarity"] >= recall.THRESHOLD


def test_nothing_below_threshold(agents, emb) -> None:
    _les("Wenn eine Datei fehlt")
    assert _pick("wie wird das wetter morgen") == []


def test_at_most_three(agents, emb) -> None:
    for i in range(5):
        _les(f"Wenn eine Datei fehlt, Fall {i}", sid=f"s{i}")
    assert len(_pick("meine datei fehlt hier")) == 3


def test_only_own_project_or_agent_scope(agents, emb) -> None:
    _les("Wenn eine Datei fehlt (p1)", scope="project:p1")
    _les("Wenn eine Datei fehlt (p2)", scope="project:p2", sid="s2")
    _les("Wenn eine Datei fehlt (ohne)", scope="agent", sid="s3")
    assert {g["cue"] for g in _pick("wo ist die datei", project="p1")} == {"Wenn eine Datei fehlt (p1)"}
    assert {g["cue"] for g in _pick("wo ist die datei", project=None)} == {"Wenn eine Datei fehlt (ohne)"}


def test_only_active(agents, emb) -> None:
    les = _les("Wenn eine Datei fehlt")
    store.set_status("a", les["id"], "retired")
    assert _pick("wo ist die datei") == []


def test_ranking_prefers_confirmed_and_confident(agents, emb) -> None:
    _les("Wenn eine Datei fehlt A", confidence="low")
    b = _les("Wenn eine Datei fehlt B", sid="s2")
    _les("Wenn eine Datei fehlt B", sid="s3")                                      # B bestätigt
    got = _pick("wo ist die datei")
    assert got[0]["id"] == b["id"] and got[0]["confirmations"] == 1


def test_short_input_is_ignored(agents, emb) -> None:
    _les("Wenn eine Datei fehlt")
    assert _pick("datei?") == [] and emb.calls == []


def test_no_lessons_no_embedding_call(agents, emb) -> None:
    assert _pick("die datei finde ich nicht") == [] and emb.calls == []


def test_cue_vector_is_cached_on_first_use(agents, emb) -> None:
    _les("Wenn eine Datei fehlt")
    _pick("die datei finde ich nicht")
    _pick("die datei finde ich wieder nicht")
    cue_calls = [c for c in emb.calls if c[1] == "db"]
    assert len(cue_calls) == 1                                                      # zweites Mal aus der Ablage
    assert store.current("a")[0]["cue_model"] == "test/emb"


def test_new_embed_model_recomputes(agents, emb, monkeypatch) -> None:
    _les("Wenn eine Datei fehlt")
    _pick("die datei finde ich nicht")
    monkeypatch.setattr(recall, "_embed_model", lambda: "test/emb2")
    _pick("die datei finde ich nicht")
    assert len([c for c in emb.calls if c[1] == "db"]) == 2


def test_without_embed_model_word_match(agents, monkeypatch) -> None:
    monkeypatch.setattr(recall, "_embed_model", lambda: "")
    _les("Wenn eine Datei im Workspace fehlt")
    _les("Wenn der Chat hängt", sid="s2")
    assert [g["cue"] for g in _pick("die Datei im Workspace finde ich nicht")] == ["Wenn eine Datei im Workspace fehlt"]
    assert _pick("diese Datei bitte") == []                                         # nur ein gemeinsames Wort (Datei)


def test_embedding_error_never_breaks(agents, monkeypatch) -> None:
    async def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(recall, "_embed", boom)
    monkeypatch.setattr(recall, "_embed_model", lambda: "test/emb")
    _les("Wenn eine Datei fehlt")
    assert _pick("die datei finde ich nicht") == []


# --- gezeigt zählen --------------------------------------------------------------------------------------------------

def test_shown_is_counted(agents, emb) -> None:
    les = _les("Wenn eine Datei fehlt")
    _pick("die datei finde ich nicht")
    _pick("die datei finde ich nicht")
    cur = store.current("a")[0]
    assert cur["id"] == les["id"] and cur["shown"] == 2 and cur["confirmations"] == 0


# --- Darstellung -----------------------------------------------------------------------------------------------------

def test_render_block() -> None:
    from hydrahive.runner.system_prompt import render_lessons_block
    assert render_lessons_block([]) == ""
    out = render_lessons_block([{"cue": "Wenn eine Datei fehlt", "lesson": "erst nachsehen", "part": "procedure",
                                 "confidence": "high", "confirmations": 2}])
    assert "Lehren aus früheren Aufgaben (mit Beleg)" in out and "prüfe, ob sie hier gelten" in out
    assert "- WENN Wenn eine Datei fehlt → erst nachsehen [procedure, high, ×2 bestätigt]" in out
    one = render_lessons_block([{"cue": "c", "lesson": "l", "part": "tool", "confidence": "low", "confirmations": 0}])
    assert "[tool, low]" in one


def test_compose_puts_lessons_in_volatile_part(tmp_path) -> None:
    from hydrahive.runner.system_prompt import compose
    lessons = [{"cue": "Wenn X", "lesson": "Y", "part": "tool", "confidence": "high", "confirmations": 0}]
    stable, volatile, _ = compose("basis", extra_system=None, workspace=tmp_path, summary=None, skills=None,
                                  longterm_memory=False, tool_schemas=[], allowed_tools=[], lessons=lessons)
    assert "WENN Wenn X" in volatile and "WENN" not in stable


def test_runner_recalls_before_first_call() -> None:
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "src/hydrahive/runner/runner.py").read_text()
    loop = src.index("for iteration in range(max_iterations):")
    assert "recall_lessons(" in src[:loop]                                          # einmal je Eingabe, vor der Schleife
    assert "lessons=recalled_lessons" in src[loop:]


def test_runner_recall_never_raises(monkeypatch) -> None:
    from hydrahive.runner import _runner_lessons

    async def boom(*a, **k):
        raise RuntimeError("weg")
    monkeypatch.setattr(recall, "pick", boom)
    assert asyncio.run(_runner_lessons.recall_lessons("a", "irgendeine längere eingabe hier", "p1")) == []


def test_word_match_ignores_filler_words(agents, monkeypatch) -> None:
    monkeypatch.setattr(recall, "_embed_model", lambda: "")
    _les("Wenn eine Datei im Workspace fehlt")
    assert _pick("wenn eine nicht dann") == []                                      # nur Füllwörter gemeinsam
    assert _pick("eine Datei bitte") == []                                          # Füllwort + ein echtes Wort
