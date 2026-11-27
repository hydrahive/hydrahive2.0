"""Katalog Etappe 4, Aufgabe 5: tool_mode catalog im Runner und Prompt (Spec V2/V4/V6/E4, K1, K4, K7).

K7 zuerst: Der Snapshot ``fixtures/catalog_classic_snapshot.json`` wurde mit dem Code von main (ec552ce1) VOR jeder Änderung
erzeugt (Schema-Liste und stabiler System-Prompt zweier classic-Agenten). Er darf sich nie ändern müssen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from _catalog_mode_world import CLASSIC_TOOLS, World, snapshot  # noqa: E402

SNAP = json.loads((Path(__file__).parent / "fixtures" / "catalog_classic_snapshot.json").read_text())
KATALOG = ["find_tools", "find_skills", "run_tool"]


@pytest.fixture
def world(client, monkeypatch):
    w = World(client, monkeypatch)
    yield w
    w.cleanup()


def _names(call) -> list[str]:
    return [t["name"] for t in call["tools"]]


def _tu(call_id: str, tool: str, **inp) -> dict:
    return {"type": "tool_use", "id": call_id, "name": tool, "input": inp}


# ── K7: classic exakt wie vorher ──────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name, extra", [("classic_default", {}), ("classic_longterm", {"longterm_memory": True})])
def test_classic_payload_unveraendert(world, name, extra):
    call = world.run(world.session(world.agent(**extra)))[0]
    assert snapshot(call) == SNAP[name]


def test_tool_mode_standard_classic_und_validierung(world):
    from hydrahive.agents import config as agent_config
    from hydrahive.agents._validation import AgentValidationError
    aid = world.agent()
    assert agent_config.get(aid)["tool_mode"] == "classic"
    assert agent_config.get(aid)["pinned_tools"] == []
    with pytest.raises(AgentValidationError):
        agent_config.update(aid, tool_mode="wild")
    assert agent_config.update(aid, tool_mode="catalog")["tool_mode"] == "catalog"
    with pytest.raises(AgentValidationError):
        agent_config.update(aid, pinned_tools="file_read")          # muss eine Liste sein


def test_classic_agent_ohne_feld_gleich_classic(world):
    """Ein Agent, dessen Config das Feld nie hatte (Altbestand), läuft wie classic."""
    from hydrahive.agents import config as agent_config
    from hydrahive.agents._config_utils import config_path
    aid = world.agent()
    p = config_path(aid)
    cfg = json.loads(p.read_text())
    cfg.pop("tool_mode", None)
    cfg.pop("pinned_tools", None)
    p.write_text(json.dumps(cfg))
    assert agent_config.get(aid)["tool_mode"] == "classic"
    assert snapshot(world.run(world.session(aid))[0]) == SNAP["classic_default"]


# ── K1: catalog schickt nur Kern ∩ Freigabe, pinned, remembered ───────────────────────────────────────────────────

def test_catalog_schickt_nur_kern_pinned_remembered(world):
    from hydrahive.runner._catalog_mode import catalog_schema_names
    eff = ["shell_exec", "file_read", "web_search", "send_mail", "todo_write", "read_mail", "generate_image"]
    got = catalog_schema_names(eff + KATALOG, ["send_mail", "nicht_frei"], ["generate_image", "send_mail", "shell_exec"])
    assert got == ["shell_exec", "file_read", "todo_write", *KATALOG, "send_mail", "generate_image"]
    assert "web_search" not in got and "read_mail" not in got and "nicht_frei" not in got

    aid = world.agent(tool_mode="catalog", pinned_tools=["send_mail"])
    call = world.run(world.session(aid))[0]
    # Reihenfolge wie CORE_TOOLS im Plan, dann angeheftete
    assert _names(call) == ["shell_exec", "file_read", "file_write", "todo_write", *KATALOG, "load_skill", "send_mail"]
    assert "web_search" not in _names(call)


def test_kern_erweitert_keine_rechte(world):
    """D6: Ein Agent ohne shell_exec bekommt es auch im catalog-Modus nicht – weder im Schema noch über run_tool."""
    aid = world.agent(tools=["file_read", "load_skill"], tool_mode="catalog", pinned_tools=["shell_exec"])
    call = world.run(world.session(aid))[0]
    assert "shell_exec" not in _names(call) and "file_write" not in _names(call)
    assert _names(call) == ["file_read", *KATALOG, "load_skill"]


def test_run_tool_erreicht_alles_freigegebene_nicht_mehr(world):
    """allowed_tools = volle Freigabe + Katalog-Werkzeuge: web_search (freigegeben, nicht im Schema) läuft über run_tool,
    das nicht freigegebene send_mail … wird abgelehnt."""
    aid = world.agent(tools=["file_read", "web_search", "load_skill"], tool_mode="catalog")
    world.script = [[_tu("c1", "run_tool", name="web_search", args={"query": "x"}),
                     _tu("c2", "run_tool", name="send_mail", args={})],
                    [{"type": "text", "text": "fertig"}]]
    world.monkeypatch.setattr("hydrahive.runner._runner_tools.execute_tool", _fake_exec(world))
    world.run(world.session(aid))
    assert world.executed == ["web_search"]


def _fake_exec(world):
    from hydrahive.tools.base import ToolResult
    world.executed = []

    async def fake(*, tool_use, allowed_tools, ctx, parent_message_id, iteration=None):
        if tool_use["name"] not in allowed_tools:
            return ToolResult.fail("nicht erlaubt"), None, 0
        world.executed.append(tool_use["name"])
        return ToolResult.ok("ok"), None, 1
    return fake


# ── K4: Tool-Liste im Lauf byte-gleich ────────────────────────────────────────────────────────────────────────────

def test_tool_liste_im_lauf_byte_gleich_trotz_run_tool(world):
    aid = world.agent(tool_mode="catalog")
    sid = world.session(aid)
    world.script = [[_tu("c1", "find_tools", query="Mail schicken")],
                    [_tu("c2", "run_tool", name="send_mail", args={"to": "a@b.de", "subject": "s", "body": "b"})],
                    [{"type": "text", "text": "fertig"}]]
    world.monkeypatch.setattr("hydrahive.runner._runner_tools.execute_tool", _fake_exec(world))
    calls = world.run(sid)
    assert len(calls) == 3
    ersten = json.dumps(calls[0]["tools"], sort_keys=True)
    assert all(json.dumps(c["tools"], sort_keys=True) == ersten for c in calls)
    assert all(c["stable"] == calls[0]["stable"] for c in calls)         # auch der Prompt bleibt byte-gleich
    assert world.executed == ["find_tools", "send_mail"]                  # find_tools direkt, send_mail über run_tool
    from hydrahive.db import sessions as sessions_db
    assert sessions_db.get(sid).metadata["catalog_remembered"] == ["send_mail"]   # find_tools wird nie vorgemerkt


# ── Vormerken (E4, Review-Fokus 5) ────────────────────────────────────────────────────────────────────────────────

def test_remembered_erst_naechster_lauf(world):
    from hydrahive.db import sessions as sessions_db
    aid = world.agent(tool_mode="catalog")
    sid = world.session(aid)
    world.script = [[_tu("c1", "run_tool", name="send_mail", args={"to": "a@b.de", "subject": "s", "body": "b"})],
                    [{"type": "text", "text": "fertig"}]]
    world.monkeypatch.setattr("hydrahive.runner._runner_tools.execute_tool", _fake_exec(world))
    erster = world.run(sid)
    assert all("send_mail" not in _names(c) for c in erster)              # im selben Lauf nie
    assert sessions_db.get(sid).metadata["catalog_remembered"] == ["send_mail"]
    zweiter = world.run(sid)[0]
    assert "send_mail" in _names(zweiter)                                  # erst im nächsten Lauf


def test_remembered_obergrenze(world):
    from hydrahive.db import sessions as sessions_db
    from hydrahive.runner._catalog_mode import REMEMBER_MAX, remember
    aid = world.agent(tool_mode="catalog")
    sid = world.session(aid)
    assert REMEMBER_MAX == 15
    for i in range(20):
        remember(sid, f"tool_{i}")
    got = sessions_db.get(sid).metadata["catalog_remembered"]
    assert len(got) == 15 and got[0] == "tool_5" and got[-1] == "tool_19"  # älteste raus
    remember(sid, "tool_10")                                               # erneut benutzt → ans Ende, keine Dublette
    got = sessions_db.get(sid).metadata["catalog_remembered"]
    assert got[-1] == "tool_10" and got.count("tool_10") == 1 and len(got) == 15


def test_remembered_nicht_freigegebenes_wird_nie_gesendet(world):
    """Ein vorgemerktes Tool, das der Agent (inzwischen) nicht mehr darf, geht nicht ans Modell."""
    from hydrahive.runner._catalog_mode import remember
    aid = world.agent(tools=["file_read", "load_skill"], tool_mode="catalog")
    sid = world.session(aid)
    remember(sid, "shell_exec")
    assert "shell_exec" not in _names(world.run(sid)[0])


def test_nur_run_tool_ueber_katalog_wird_vorgemerkt(world):
    """Ein direkt aufgerufenes Tool (z. B. aus dem Kern) wird nicht vorgemerkt – nur, was über run_tool kam."""
    from hydrahive.db import sessions as sessions_db
    aid = world.agent(tool_mode="catalog")
    sid = world.session(aid)
    world.script = [[_tu("c1", "file_read", path="x")], [{"type": "text", "text": "ok"}]]
    world.monkeypatch.setattr("hydrahive.runner._runner_tools.execute_tool", _fake_exec(world))
    world.run(sid)
    assert not (sessions_db.get(sid).metadata or {}).get("catalog_remembered")


# ── Umschalten mitten in der Sitzung (Review-Fokus 3) ─────────────────────────────────────────────────────────────

def test_umschalten_catalog_classic_mitten_in_sitzung(world):
    from hydrahive.agents import config as agent_config
    aid = world.agent(tool_mode="catalog")
    sid = world.session(aid)
    a = world.run(sid, "eins")[0]
    agent_config.update(aid, tool_mode="classic")
    b = world.run(sid, "zwei")[0]
    agent_config.update(aid, tool_mode="catalog")
    c = world.run(sid, "drei")[0]
    assert _names(a) == _names(c) and _names(b) == CLASSIC_TOOLS                 # classic: exakt die Config
    assert "find_tools" in _names(a) and "find_tools" not in _names(b)
    assert "## Kategorien" in a["stable"] and "## Kategorien" not in b["stable"]
    assert "## Skills" in b["stable"]


# ── Prompt (V4/V6) ────────────────────────────────────────────────────────────────────────────────────────────────

def test_catalog_prompt_kategorien_statt_skill_tabelle(world):
    aid = world.agent(tools=["file_read", "web_search", "read_memory", "load_skill"], tool_mode="catalog")
    st = world.run(world.session(aid))[0]["stable"]
    assert "## Kategorien" in st and "## Skills" not in st and "| Skill | Wann nutzen |" not in st
    assert "`files`" in st and "`web`" in st and "`memory`" in st
    assert "`mail`" not in st and "`media`" not in st                         # keine Kategorie ohne eigenes Tool
    assert "find_tools" in st and "find_skills" in st and "run_tool" in st


def test_catalog_prompt_zeigt_angeheftete_skills_nicht_alle(world):
    aid = world.agent(tool_mode="catalog", pinned_skills=["debugging"])
    st = world.run(world.session(aid))[0]["stable"]
    assert "`debugging`" in st and "`docs`" not in st


def test_catalog_prompt_stabil_ueber_mehrere_laeufe(world):
    aid = world.agent(tool_mode="catalog")
    sid = world.session(aid)
    assert world.run(sid, "eins")[0]["stable"] == world.run(sid, "zwei")[0]["stable"]



# ── Review #785 ──────────────────────────────────────────────────────────────────────────────────────────────────

def test_catalog_prompt_hint_nur_fuer_gezeigte_tools(world, monkeypatch):
    """Fängt (Review #785, sollte): Hinweise kamen für ALLE freigegebenen Tools in den Prompt, auch nicht gezeigte."""
    from hydrahive.tools import REGISTRY
    import dataclasses
    monkeypatch.setitem(REGISTRY, "send_mail", dataclasses.replace(REGISTRY["send_mail"], prompt_hint="HINWEIS-MAIL"))
    monkeypatch.setitem(REGISTRY, "file_read", dataclasses.replace(REGISTRY["file_read"], prompt_hint="HINWEIS-DATEI"))
    aid = world.agent(tool_mode="catalog")                       # send_mail freigegeben, aber nicht im Kern
    call = world.run(world.session(aid))[0]
    assert "HINWEIS-DATEI" in call["stable"]                     # gezeigt → Hinweis da
    assert "HINWEIS-MAIL" not in call["stable"]                  # nicht gezeigt → kein Hinweis
    cid = world.agent()                                          # classic: wie bisher alle
    assert "HINWEIS-MAIL" in world.run(world.session(cid))[0]["stable"]


def test_find_tools_liefert_prompt_hint_mit():
    import asyncio
    import dataclasses
    from unittest.mock import patch
    from hydrahive.tools import REGISTRY
    from hydrahive.tools import find_tools as ft
    t = dataclasses.replace(REGISTRY["send_mail"], prompt_hint="HINWEIS-MAIL")
    with patch.dict(REGISTRY, {"send_mail": t}):
        assert ft._prompt_hint("send_mail") == "HINWEIS-MAIL"
        assert ft._prompt_hint("gibt_es_nicht") == ""
    assert asyncio.iscoroutinefunction(ft._execute)


def test_catalog_mit_longterm_memory_ueber_mehrere_iterationen_stabil(world):
    """Review #785 (kann): _inject_longterm_memory hängt in-place an – im catalog-Modus darf nichts wachsen."""
    aid = world.agent(tool_mode="catalog", longterm_memory=True)
    sid = world.session(aid)
    world.script = [[_tu("c1", "find_tools", query="Mail schicken")], [_tu("c2", "find_tools", query="Bild")],
                    [{"type": "text", "text": "fertig"}]]
    world.monkeypatch.setattr("hydrahive.runner._runner_tools.execute_tool", _fake_exec(world))
    calls = world.run(sid)
    assert len(calls) == 3
    namen = [[t["name"] for t in c["tools"]] for c in calls]
    assert namen[0] == namen[1] == namen[2] and len(namen[0]) == len(set(namen[0]))
    assert calls[0]["stable"] == calls[1]["stable"] == calls[2]["stable"]


def test_handoff_ueberschreibt_vorgemerktes_nicht(world):
    """Fängt (Review #785, sollte): Handoff schrieb metadata komplett aus altem Stand – catalog_remembered ging verloren."""
    from hydrahive.db import sessions as sessions_db
    sid = world.session(world.agent(tool_mode="catalog"))
    alt = sessions_db.get(sid)                                    # Stand, den der Handoff früher gelesen hätte
    sessions_db.remember_catalog_tool(sid, "send_mail", 15)       # parallel vorgemerkt
    sessions_db.merge_metadata(sid, {"incoming_state_id": "st-1"}, status="active")
    md = sessions_db.get(sid).metadata
    assert md["catalog_remembered"] == ["send_mail"] and md["incoming_state_id"] == "st-1"
    assert alt.metadata.get("catalog_remembered") is None


def test_handoff_setup_nutzt_merge_metadata():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "src/hydrahive/runner/_handoff_setup.py").read_text()
    assert "merge_metadata(" in src and "update(session.id, status=\"active\", metadata=" not in src
