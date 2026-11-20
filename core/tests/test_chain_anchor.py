"""Ketten-Anker: Zielbild + Originalauftrag reisen unverändert durch jede Ebene.

Befund 20.11.2026 („stille Post“): Der Projekt-Agent schrieb Tills Auftrag für
jeden Spezialisten neu, dabei fielen Kernpunkte weg. Diese Tests prüfen, dass
das jetzt im CODE verhindert ist, unabhängig davon, was ein Agent schreibt.
"""
from __future__ import annotations

import asyncio

from hydrahive.agentlink import chain_anchor as ca
from hydrahive.agentlink.protocol import State, TaskBlock
from hydrahive.db import agent_handoffs as db_handoffs
from hydrahive.tools import ask_agent
from tests.test_background_delegation import _ctx

pytest_plugins = ["tests.test_background_delegation"]

ORIGINAL = "Baue X. Kernpunkt A: Zahlungen NICHT angehakt. Kernpunkt B: Live-Gegencheck mit echten Daten."
ZIEL = "# Ziel\nTill kann X.\n## Abnahme\n- A1 Till sieht Y"


# ---------------------------------------------------------------- reine Funktionen

def test_compose_extract_roundtrip():
    text = ca.compose("eigener Text", {}, ziel=ca.Block("ziel", ZIEL, "ziele/x.md"))
    blocks = ca.extract(text)
    assert blocks["ziel"].body == ZIEL and blocks["ziel"].source == "ziele/x.md"
    assert blocks["original"].body == "eigener Text"


def test_geerbte_bloecke_haben_vorrang_vor_eigenem_text():
    inh = ca.extract(ca.compose(ORIGINAL, {}, ziel=ca.Block("ziel", ZIEL)))
    umgeschrieben = "Mach X irgendwie."          # der Projekt-Agent formuliert neu und lässt Punkte weg
    out = ca.extract(ca.compose(umgeschrieben, inh, ziel=ca.Block("ziel", "ANDERES ZIEL")))
    assert out["original"].body == ORIGINAL       # Original bleibt Tills Text
    assert out["ziel"].body == ZIEL               # geerbtes Ziel lässt sich nicht ersetzen


def test_manipulierter_block_gilt_nicht():
    text = ca.compose(ORIGINAL, {})
    kaputt = text.replace("NICHT angehakt", "angehakt")      # Inhalt geändert, Prüfsumme alt
    assert "original" not in ca.extract(kaputt)


def test_strip_entfernt_auch_beschaedigte_bloecke():
    text = ca.compose(ORIGINAL, {}).replace("Kernpunkt A", "Kernpunkt Z")
    assert "<!--hh-" not in ca.strip(text) and "Originalauftrag" not in ca.strip(text)


def test_keine_verdopplung_bei_mehrfachem_compose():
    t1 = ca.compose(ORIGINAL, {})
    t2 = ca.compose(t1, ca.extract(t1))
    t3 = ca.compose(t2, ca.extract(t2))
    assert t3.count("<!--hh-original") == 1


# ---------------------------------------------------------------- über ask_agent + Handoff-Setup

def _send(args, ctx):
    async def scenario():
        res = await ask_agent._execute(args, ctx)
        for t in list(asyncio.all_tasks()):
            if t.get_name().startswith("delegation-"):
                t.cancel()
        return res
    return asyncio.run(scenario())


def test_zwei_ebenen_original_kommt_unveraendert_an(spec_agent, session_id, agentlink, starter, tmp_path):
    """Reproduktion „stille Post“: Buddy → Projekt-Agent → Spezialist.

    Ebene 1 (Chat/Buddy) schickt ORIGINAL + Ziel. Ebene 2 (Handoff-Lauf des Projekt-Agenten)
    schreibt einen eigenen, verkürzten Auftrag. Beim Spezialisten müssen Ziel und ORIGINAL
    trotzdem wörtlich ankommen."""
    posted, _ = agentlink
    (tmp_path / "ziele").mkdir()
    (tmp_path / "ziele" / "x.md").write_text(ZIEL, encoding="utf-8")

    r1 = _send({"agent_id": spec_agent["id"], "task": ORIGINAL, "goal": "g", "deliverable": "d",
                "ziel_doc": "ziele/x.md", "abnahme": ["A1"]}, _ctx(session_id, tmp_path))
    assert r1.success, r1.error
    stufe1 = posted[-1].task.description

    # Empfang beim Projekt-Agenten simulieren: Handoff-Setup merkt sich die Anker seiner Session.
    from hydrahive.runner import _handoff_setup as hs
    from hydrahive.db import sessions as sessions_db
    pa_session = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="pa").id
    rec = db_handoffs.create(incoming_state_id="in-1", from_agent="buddy", agent_id="pa", session_id=pa_session)
    hs._remember_anchor(rec["id"], State(agent_id="buddy", task=TaskBlock(type="feature", description=stufe1)))

    # Projekt-Agent (Handoff-Lauf) gibt einen umgeschriebenen, gekürzten Auftrag weiter – OHNE ziel_doc.
    r2 = _send({"agent_id": spec_agent["id"], "task": "Mach X irgendwie.", "goal": "g", "deliverable": "d"},
               _ctx(pa_session, tmp_path, origin="handoff", depth=1))
    assert r2.success, r2.error
    stufe2 = ca.extract(posted[-1].task.description)
    assert stufe2["original"].body.startswith(ORIGINAL)       # Tills Text, nicht der des Projekt-Agenten
    assert "Kernpunkt A" in stufe2["original"].body and "Kernpunkt B" in stufe2["original"].body
    assert stufe2["ziel"].body == ZIEL
    assert stufe2["abnahme"].body == "- A1 Till sieht Y"          # Abnahme reist ebenfalls mit
    assert "Mach X irgendwie." in posted[-1].task.description   # eigener Text darf ergänzen


def test_ziel_doc_fehlt_auftrag_wird_nicht_abgeschickt(spec_agent, session_id, agentlink, starter, tmp_path):
    posted, _ = agentlink
    r = _send({"agent_id": spec_agent["id"], "task": "x", "goal": "g", "deliverable": "d",
               "ziel_doc": "ziele/gibts-nicht.md"}, _ctx(session_id, tmp_path))
    assert r.success is False and "Zieldokument" in r.error
    assert posted == []


def test_ziel_doc_ausserhalb_workspace_abgelehnt(spec_agent, session_id, agentlink, starter, tmp_path):
    posted, _ = agentlink
    r = _send({"agent_id": spec_agent["id"], "task": "x", "goal": "g", "deliverable": "d",
               "ziel_doc": "../../etc/passwd"}, _ctx(session_id, tmp_path))
    assert r.success is False and "außerhalb" in r.error
    assert posted == []


def test_ohne_kette_und_ohne_ziel_wird_original_trotzdem_gesetzt(spec_agent, session_id, agentlink, starter, tmp_path):
    posted, _ = agentlink
    r = _send({"agent_id": spec_agent["id"], "task": ORIGINAL, "goal": "g", "deliverable": "d"}, _ctx(session_id, tmp_path))
    assert r.success
    b = ca.extract(posted[-1].task.description)
    assert "ziel" not in b and b["original"].body.startswith(ORIGINAL)
