"""Ausgelagerte Vorbereitung von ask_agent (Refactor 14.11.2026)."""
from __future__ import annotations

from hydrahive.tools import _ask_agent_prepare as prep


def test_map_context_komfort_schluessel():
    desc, files, errors = prep.map_context("Mach X", {
        "errors": ["e1"], "error_log": "log", "files": [{"path": "a"}],
        "related_files": ["b"], "code_snippet": "print(1)"})
    # Objekte statt Text: AgentLink verlangt ErrorContext{type, message} (Task 54c50a91)
    assert [(e.type, e.message) for e in errors] == [("error", "e1"), ("error_log", "log")]
    assert files == [{"path": "a"}, {"path": "b"}]
    assert desc == "Mach X\n\n```\nprint(1)\n```"


def test_map_context_leer():
    assert prep.map_context("T", {}) == ("T", [], [])


def test_projekt_agent_nur_freigegebene(monkeypatch):
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    monkeypatch.setattr(ac, "get", lambda aid: {"type": "project", "project_id": "p1"})
    monkeypatch.setattr(pc, "get", lambda pid: {"allowed_specialists": ["s1"]})
    assert prep.project_refusal("pa", "s1") is None
    assert "nicht freigegeben" in prep.project_refusal("pa", "s2")


def test_andere_agenten_ohne_einschraenkung(monkeypatch):
    from hydrahive.agents import config as ac
    monkeypatch.setattr(ac, "get", lambda aid: {"type": "specialist"})
    assert prep.project_refusal("x", "beliebig") is None


def test_tote_ids_in_allowed_specialists_sperren_nicht(monkeypatch):
    """Altlast auf bestehenden Servern (vor diesem Fix von Hand entfernt, 15.11.2026): Projekte mit nur einer
    toten ID in allowed_specialists dürfen trotzdem Spezialisten beauftragen — die tote ID zählt nicht als
    Einschränkung."""
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc

    def fake_agent_get(aid):
        if aid == "pa":
            return {"type": "project", "project_id": "p1"}
        if aid == "s1":
            return {"id": "s1", "type": "specialist"}
        return None  # "tote-id": Agent existiert nicht mehr

    monkeypatch.setattr(ac, "get", fake_agent_get)
    monkeypatch.setattr(pc, "get", lambda pid: {"allowed_specialists": ["tote-id"]})
    assert prep.project_refusal("pa", "s1") is None


def test_lebende_freigabe_neben_toter_id_wirkt_weiter(monkeypatch):
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc

    def fake_agent_get(aid):
        if aid == "pa":
            return {"type": "project", "project_id": "p1"}
        if aid == "s1":
            return {"id": "s1", "type": "specialist"}
        return None

    monkeypatch.setattr(ac, "get", fake_agent_get)
    monkeypatch.setattr(pc, "get", lambda pid: {"allowed_specialists": ["tote-id", "s1"]})
    assert prep.project_refusal("pa", "s1") is None
    assert "nicht freigegeben" in prep.project_refusal("pa", "s2")
