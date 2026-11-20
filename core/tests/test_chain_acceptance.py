"""Ketten-Anker Etappe 2+3: Ziel-Pflicht für Projektarbeit und Abnahme per Skript.

Befund 20.11.2026: Fertig-Meldungen ohne Bezug zum Ziel („grüne Tests gegen das
falsche Ziel“). Jetzt prüft der KERN den Bericht gegen die Abnahme-Punkte und
meldet sonst „incomplete“ – unabhängig davon, was der Agent über sich behauptet.
"""
from __future__ import annotations

import pytest

from hydrahive.agentlink import acceptance
from hydrahive.agentlink import chain_anchor as ca
from hydrahive.agentlink.protocol import State, TaskBlock
from hydrahive.db import agent_handoffs as db_handoffs
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import _handoff_acceptance, _handoff_setup
from hydrahive.tools import _ask_agent_anchor as anchor
from tests.test_background_delegation import _ctx
from tests.test_chain_anchor import _send

pytest_plugins = ["tests.test_background_delegation"]

ZIEL = """# Ziel
Till kann X.
## Abnahme
| # | Till kann … | Prüfung | Stand |
|---|---|---|---|
| A1 | Konten sehen | Konten-Seite | ❌ |
| A2 | Bestand je Coin | Wert = Cryptoboard | 🟡 |
- B1 Swaps als Umbuchung
"""
PROJECT = {"id": "pa", "type": "project"}


def _write(tmp_path):
    (tmp_path / "ziele").mkdir(exist_ok=True)
    (tmp_path / "ziele" / "x.md").write_text(ZIEL, encoding="utf-8")


# ---------------------------------------------------------------- Abnahme-Skript

def test_punkte_aus_tabelle_und_liste():
    assert list(acceptance.points_from_ziel(ZIEL)) == ["A1", "A2", "B1"]


def test_bericht_vollstaendig_mit_beleg():
    body = acceptance.body_for(acceptance.points_from_ziel(ZIEL), ["A1", "A2"])
    report = ("Fertig.\n| Punkt | Stand | Beleg |\n|---|---|---|\n| A1 | ✅ | GET /konten → 3 Konten |\n"
              "| A2 | ✅ erfüllt | 1.234,56 € = Cryptoboard |")
    assert acceptance.check_report(body, report).complete


@pytest.mark.parametrize("report,feld", [
    ("| A1 | ✅ | GET /konten |", "missing"),                       # A2 fehlt
    ("| A1 | ✅ | GET /konten |\n| A2 | ❌ | Kurs fehlt |", "open"),  # A2 nicht erfüllt
    ("| A1 | ✅ | GET /konten |\n| A2 | ✅ | — |", "no_evidence"),   # A2 ohne Beleg
    ("Alles fertig, alle Tests grün!", "missing"),                    # Nacherzählung statt Tabelle
])
def test_bericht_unvollstaendig(report, feld):
    body = acceptance.body_for(acceptance.points_from_ziel(ZIEL), ["A1", "A2"])
    v = acceptance.check_report(body, report)
    assert not v.complete and "A2" in getattr(v, feld)


# ---------------------------------------------------------------- Etappe 2: Ziel-Pflicht + Auswahl

def test_projektarbeit_ohne_ziel_wird_abgelehnt(session_id, tmp_path):
    with pytest.raises(anchor.AnchorError, match="braucht ein Zieldokument"):
        anchor.anchor_task("Baue X", {"task_type": "feature"}, _ctx(session_id, tmp_path), PROJECT)


def test_frage_an_projekt_agent_ohne_ziel_erlaubt(session_id, tmp_path):
    out = anchor.anchor_task("Wie viele Tests?", {"task_type": "research"}, _ctx(session_id, tmp_path), PROJECT)
    assert "original" in ca.extract(out)


def test_ziel_mit_punkten_verlangt_auswahl(session_id, tmp_path):
    _write(tmp_path)
    with pytest.raises(anchor.AnchorError, match="abnahme fehlt.*A1, A2, B1"):
        anchor.anchor_task("Baue X", {"ziel_doc": "ziele/x.md"}, _ctx(session_id, tmp_path), PROJECT)


def test_unbekannter_punkt_abgelehnt(session_id, tmp_path):
    _write(tmp_path)
    with pytest.raises(anchor.AnchorError, match="Z9"):
        anchor.anchor_task("Baue X", {"ziel_doc": "ziele/x.md", "abnahme": ["A1", "Z9"]},
                           _ctx(session_id, tmp_path), PROJECT)


def test_kette_kann_abnahme_nur_einschraenken_nicht_ausweiten(spec_agent, session_id, agentlink, starter, tmp_path):
    """Ebene 1 verlangt A1+A2. Der Projekt-Agent darf einem Spezialisten A2 geben, aber nicht B1
    hinzufügen; gibt er nichts an, reist der volle geerbte Umfang mit (kein stilles Weglassen)."""
    posted, _ = agentlink
    _write(tmp_path)
    r1 = _send({"agent_id": spec_agent["id"], "task": "Baue X", "goal": "g", "deliverable": "d",
                "ziel_doc": "ziele/x.md", "abnahme": ["a1", "A2"]}, _ctx(session_id, tmp_path))
    assert r1.success, r1.error
    stufe1 = ca.extract(posted[-1].task.description)
    assert acceptance.ids_in(stufe1["abnahme"].body) == ["A1", "A2"]

    pa = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="pa").id
    rec = db_handoffs.create(incoming_state_id="in-2", from_agent="buddy", agent_id="pa", session_id=pa)
    _handoff_setup._remember_anchor(rec["id"], State(agent_id="b", task=TaskBlock(
        type="feature", description=posted[-1].task.description)))
    hctx = _ctx(pa, tmp_path, origin="handoff", depth=1)

    r_aus = _send({"agent_id": spec_agent["id"], "task": "t", "goal": "g", "deliverable": "d", "abnahme": ["B1"]}, hctx)
    assert r_aus.success is False and "B1" in r_aus.error
    r_teil = _send({"agent_id": spec_agent["id"], "task": "t", "goal": "g", "deliverable": "d", "abnahme": ["A2"]}, hctx)
    assert r_teil.success and acceptance.ids_in(ca.extract(posted[-1].task.description)["abnahme"].body) == ["A2"]
    r_ohne = _send({"agent_id": spec_agent["id"], "task": "t", "goal": "g", "deliverable": "d"}, hctx)
    assert r_ohne.success and acceptance.ids_in(ca.extract(posted[-1].task.description)["abnahme"].body) == ["A1", "A2"]


# ---------------------------------------------------------------- Etappe 3: Kern setzt den Status

def _handoff_with_abnahme(ids):
    sid = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="sp").id
    rec = db_handoffs.create(incoming_state_id=f"in-{sid}", from_agent="pa", agent_id="sp", session_id=sid)
    body = acceptance.body_for(acceptance.points_from_ziel(ZIEL), ids)
    text = ca.compose("Baue X", {}, ziel=ca.Block("ziel", ZIEL), abnahme=ca.Block("abnahme", body))
    _handoff_setup._remember_anchor(rec["id"], State(agent_id="pa", task=TaskBlock(type="feature", description=text)))
    return rec["id"]


def test_kern_meldet_unvollstaendig_statt_fertig(session_id):
    hid = _handoff_with_abnahme(["A1", "A2"])
    status, out = _handoff_acceptance.apply(hid, "done", "Alles fertig, 30 Tests grün.", "Alles fertig")
    assert status == "incomplete" and "UNVOLLSTÄNDIG" in out and "A1: fehlt im Bericht" in out


def test_kern_meldet_fertig_bei_vollstaendiger_abnahme(session_id):
    hid = _handoff_with_abnahme(["A1"])
    status, out = _handoff_acceptance.apply(hid, "done", "| A1 | ✅ | curl /konten → 3 |", "x")
    assert status == "done" and "ALLE Punkte" in out


def test_ohne_abnahme_bleibt_alles_wie_bisher(session_id):
    sid = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="alt").id
    rec = db_handoffs.create(incoming_state_id=f"in-{sid}", from_agent="pa", agent_id="sp", session_id=sid)
    assert _handoff_acceptance.apply(rec["id"], "done", "ok", "ok") == ("done", "ok")
    assert _handoff_acceptance.apply(rec["id"], "error", "x", "x") == ("error", "x")


def test_unvollstaendig_kommt_beim_auftraggeber_als_incomplete_an():
    """Antwort-State → delegation_watch: „Unvollständig:“ darf nicht als Fehler/fertig enden."""
    from hydrahive.agentlink.protocol import WorkingMemory
    from hydrahive.runner import delegation_watch
    resp = State(agent_id="h", task=TaskBlock(type="feature", description="Unvollständig: …", status="blocked"),
                 working_memory=WorkingMemory(findings=["Bericht"]))
    assert delegation_watch.result_from_state(resp)[0] == "incomplete"
