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


class FakeJudge:
    """Ersetzt die Rückfrage beim Modell: sagt „passt“ zu allen Kandidaten (oder nach Regel), zählt Aufrufe."""

    def __init__(self, rule=None):
        self.calls, self.rule = [], rule

    async def __call__(self, messages, model=None, temperature=0.0, max_tokens=200):
        self.calls.append({"model": model, "messages": messages})
        lines = [ln for ln in messages[1]["content"].splitlines() if ln[:1].isdigit()]
        nums = [i + 1 for i, ln in enumerate(lines) if (self.rule or (lambda ln: True))(ln)]
        return '{"apply": %s}' % nums


@pytest.fixture
def emb(monkeypatch):
    fake = FakeEmbed()
    monkeypatch.setattr(recall, "_embed", fake)
    monkeypatch.setattr(recall, "_embed_model", lambda: "test/emb")
    monkeypatch.setattr(recall, "_judge_model", lambda: "test/judge")
    monkeypatch.setattr(recall, "_complete", FakeJudge())
    return fake


def _pick(text, project="p1"):
    return asyncio.run(recall.pick("a", text, project_id=project))


# --- Auswahl ---------------------------------------------------------------------------------------------------------

def test_matching_lesson_is_picked(agents, emb) -> None:
    _les("Wenn eine Datei fehlt")
    _les("Wenn der Chat hängt", sid="s2")
    got = _pick("die datei finde ich nicht")
    assert [g["cue"] for g in got] == ["Wenn eine Datei fehlt"]
    assert got[0]["similarity"] >= recall.CANDIDATE_FLOOR


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
    monkeypatch.setattr(recall, "_judge_model", lambda: "test/judge")
    monkeypatch.setattr(recall, "_complete", FakeJudge())
    _les("Wenn eine Datei im Workspace fehlt")
    _les("Wenn der Chat hängt", sid="s2")
    assert [g["cue"] for g in _pick("die Datei im Workspace finde ich nicht")] == ["Wenn eine Datei im Workspace fehlt"]
    assert _pick("diese Datei bitte") == []                                         # nur ein gemeinsames Wort (Datei)


def test_embedding_error_never_breaks(agents, monkeypatch) -> None:
    async def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(recall, "_embed", boom)
    monkeypatch.setattr(recall, "_embed_model", lambda: "test/emb")
    monkeypatch.setattr(recall, "_judge_model", lambda: "test/judge")
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
    monkeypatch.setattr(recall, "_judge_model", lambda: "test/judge")
    monkeypatch.setattr(recall, "_complete", FakeJudge())
    _les("Wenn eine Datei im Workspace fehlt")
    assert _pick("wenn eine nicht dann") == []                                      # nur Füllwörter gemeinsam
    assert _pick("eine Datei bitte") == []                                          # Füllwort + ein echtes Wort


class ScaledEmbed(FakeEmbed):
    """Auslöser unterschiedlich lang (Wiederholung) – nur echte Kosinus-Normierung macht sie gleich ähnlich."""

    async def __call__(self, texts, model, embed_type="db"):
        self.calls.append((tuple(texts), embed_type))
        return [[float(a in t.lower()) * (1 + t.count("!")) for a in self.AXES] for t in texts]


def test_similarity_is_cosine_not_raw_dot(agents, monkeypatch) -> None:
    monkeypatch.setattr(recall, "_embed", ScaledEmbed())
    monkeypatch.setattr(recall, "_embed_model", lambda: "test/emb")
    monkeypatch.setattr(recall, "_judge_model", lambda: "test/judge")
    monkeypatch.setattr(recall, "_complete", FakeJudge())
    _les("Wenn eine Datei fehlt!!!!!")                                              # langer Vektor, gleiche Richtung
    got = _pick("die datei finde ich nicht")
    assert len(got) == 1 and got[0]["similarity"] == pytest.approx(1.0, abs=0.001)


def test_confirmed_beats_unconfirmed_with_same_similarity(agents, emb) -> None:
    a = _les("Wenn eine Datei fehlt A")
    b = _les("Wenn eine Datei fehlt B", sid="s2")
    _les("Wenn eine Datei fehlt B", sid="s3")
    assert [g["id"] for g in _pick("wo ist die datei")] == [b["id"], a["id"]]


def test_high_confidence_beats_low_with_same_similarity(agents, emb) -> None:
    low = _les("Wenn eine Datei fehlt A", confidence="low")
    high = _les("Wenn eine Datei fehlt B", sid="s2", confidence="high")
    assert [g["id"] for g in _pick("wo ist die datei")] == [high["id"], low["id"]]


def test_shown_counts_only_the_picked(agents, emb) -> None:
    hit = _les("Wenn eine Datei fehlt")
    miss = _les("Wenn der Chat hängt", sid="s2")
    _pick("wo ist die datei")
    cur = {r["id"]: r for r in store.current("a")}
    assert cur[hit["id"]]["shown"] == 1 and "shown" not in cur[miss["id"]]


def test_unknown_status_is_refused(agents) -> None:
    les = _les("Wenn eine Datei fehlt")
    with pytest.raises(ValueError):
        store.set_status("a", les["id"], "kaputt")
    assert store.current("a")[0]["status"] == "active"


# --- Stufe 2: Rückfrage beim Modell (Nachtrag 20.10., Till: Weg 2) ---------------------------------------------------

def test_judge_decides_among_candidates(agents, emb, monkeypatch) -> None:
    judge = FakeJudge(rule=lambda ln: "Workspace" in ln)
    monkeypatch.setattr(recall, "_complete", judge)
    _les("Wenn eine Datei im Workspace fehlt")
    _les("Wenn eine Datei auf dem Server fehlt", sid="s2")
    got = _pick("wo ist die datei")
    assert [g["cue"] for g in got] == ["Wenn eine Datei im Workspace fehlt"]
    assert len(judge.calls) == 1 and judge.calls[0]["model"] == "test/judge"
    msgs = judge.calls[0]["messages"]
    assert "Similar words are not enough" in msgs[0]["content"] and "When unsure, it does not apply" in msgs[0]["content"]
    assert "REQUEST: wo ist die datei" in msgs[1]["content"] and "1. WHEN Wenn eine Datei" in msgs[1]["content"]


def test_judge_says_none_shows_none(agents, emb, monkeypatch) -> None:
    monkeypatch.setattr(recall, "_complete", FakeJudge(rule=lambda ln: False))
    _les("Wenn eine Datei fehlt")
    assert _pick("wo ist die datei") == []
    assert "shown" not in store.current("a")[0]                                       # nicht gezeigt → nicht gezählt


def test_no_candidates_no_judge_call(agents, emb, monkeypatch) -> None:
    judge = FakeJudge()
    monkeypatch.setattr(recall, "_complete", judge)
    _les("Wenn eine Datei fehlt")
    assert _pick("wie wird das wetter morgen") == [] and judge.calls == []


def test_at_most_five_candidates_go_to_judge(agents, emb, monkeypatch) -> None:
    judge = FakeJudge()
    monkeypatch.setattr(recall, "_complete", judge)
    for i in range(7):
        _les(f"Wenn eine Datei fehlt, Fall {i}", sid=f"s{i}")
    assert len(_pick("meine datei fehlt hier")) == 3
    assert judge.calls[0]["messages"][1]["content"].count("WHEN ") == 5


def test_judge_answer_is_checked(agents, emb, monkeypatch) -> None:
    _les("Wenn eine Datei fehlt")
    for raw in ('{"apply": [7]}', '{"apply": ["1"]}', "kaputt", '{"apply": 1}', '{"apply": [0, -1]}'):
        async def answer(*a, raw=raw, **k):
            return raw
        monkeypatch.setattr(recall, "_complete", answer)
        assert _pick("wo ist die datei") == [], raw


def test_judge_out_of_range_numbers_are_dropped_not_crashing(agents, emb, monkeypatch) -> None:
    _les("Wenn eine Datei fehlt")
    _les("Wenn eine Datei verschwindet", sid="s2")

    async def answer(*a, **k):
        return '{"apply": [2, 9]}'                                                    # 9 gibt es nicht
    monkeypatch.setattr(recall, "_complete", answer)
    got = _pick("wo ist die datei")
    assert len(got) == 1


def test_judge_apply_must_be_a_list(agents, emb, monkeypatch) -> None:
    _les("Wenn eine Datei fehlt")
    for raw in ('{"apply": "1"}', '{"apply": {"1": true}}', '{"apply": null}'):
        async def answer(*a, raw=raw, **k):
            return raw
        monkeypatch.setattr(recall, "_complete", answer)
        assert _pick("wo ist die datei") == [], raw


def test_judge_error_or_timeout_shows_nothing(agents, emb, monkeypatch) -> None:
    _les("Wenn eine Datei fehlt")

    async def boom(*a, **k):
        raise RuntimeError("weg")
    monkeypatch.setattr(recall, "_complete", boom)
    assert _pick("wo ist die datei") == []

    async def slow(*a, **k):
        await asyncio.sleep(1)
        return '{"apply": [1]}'
    monkeypatch.setattr(recall, "_complete", slow)
    monkeypatch.setattr(recall, "JUDGE_TIMEOUT", 0.05)
    assert _pick("wo ist die datei") == []


def test_no_judge_model_shows_nothing(agents, emb, monkeypatch) -> None:
    judge = FakeJudge()
    monkeypatch.setattr(recall, "_complete", judge)
    monkeypatch.setattr(recall, "_judge_model", lambda: "")
    _les("Wenn eine Datei fehlt")
    assert _pick("wo ist die datei") == [] and judge.calls == []


def test_candidate_floor_is_lower_than_old_threshold() -> None:
    assert recall.CANDIDATE_FLOOR == 0.40 and recall.CANDIDATES == 5 and recall.LIMIT == 3


def test_judge_model_is_the_lessons_model(monkeypatch) -> None:
    from hydrahive.llm import _config
    monkeypatch.setattr(_config, "load_config", lambda: {"default_model": "x/chat", "lessons_model": "y/lessons"})
    assert recall._judge_model() == "y/lessons"
    monkeypatch.setattr(_config, "load_config", lambda: {"default_model": "x/chat", "lessons_model": "off"})
    assert recall._judge_model() == ""
