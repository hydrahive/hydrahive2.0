"""Spezialisten-Antwort: Kurzfassung im Kontext, Langfassung als Datei (Plan E4 T4).

Vorher kürzte `bounded_reply` auf 12.000 Zeichen (¾ Anfang + ¼ Ende) – die Mitte fehlte.
Jetzt: kurze Antworten unverändert; lange → Kurzfassung (Abschnitt „Ergebnis“ bzw. Anfang bis Satzende) plus
Pfad zur Datei mit dem VOLLSTÄNDIGEN Text.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.runner import _handoff_report as rep


@pytest.fixture(autouse=True)
def reports(tmp_path, monkeypatch):
    monkeypatch.setattr(rep, "_reports_dir", lambda: tmp_path / "reports")
    return tmp_path / "reports"


def test_kurz_bleibt_unveraendert(reports):
    assert rep.split_reply("Alles erledigt.", key="h1", limit=2000) == "Alles erledigt."
    assert not reports.exists()


def test_lang_mitte_geht_nicht_verloren(reports):
    text = "A" * 9000 + " MITTE-WICHTIG " + "B" * 9000
    out = rep.split_reply(text, key="h2", limit=2000)
    assert len(out) <= 2000 + 400
    path = Path(out.split("Langfassung: ", 1)[1].split()[0])
    assert path.read_text() == text            # vollständig, inkl. Mitte
    assert path.parent == reports


def test_abschnitt_ergebnis_wird_kurzfassung(reports):
    text = ("## Ergebnis\nDrei Bugs gefunden, zwei behoben.\n\n## Belege\n" + "x " * 5000
            + "\n## Offene Punkte\n- Test fehlt")
    out = rep.split_reply(text, key="h3", limit=2000)
    assert out.startswith("## Ergebnis\nDrei Bugs gefunden, zwei behoben.")
    assert "Belege" not in out.split("Langfassung:")[0]
    assert "Langfassung:" in out


def test_ohne_abschnitt_bis_satzende(reports):
    text = ("Satz eins ist hier. " * 200).strip()
    out = rep.split_reply(text, key="h4", limit=500)
    head = out.split("\n\n…", 1)[0]
    assert head.endswith(".") and len(head) <= 500


def test_schluessel_sicher(reports):
    out = rep.split_reply("x" * 5000, key="../../etc/passwd", limit=100)
    path = Path(out.split("Langfassung: ", 1)[1].split()[0])
    assert path.parent == reports and ".." not in path.name


def test_schreibfehler_faellt_auf_alte_kuerzung_zurueck(reports, monkeypatch):
    def boom(*a, **k):
        raise OSError("voll")
    monkeypatch.setattr(rep, "_write", boom)
    out = rep.split_reply("A" * 20000, key="h5", limit=2000)
    assert "Antwort gekürzt" in out and len(out) <= 12_100


def test_langfassung_im_workspace_des_auftraggebers(client, tmp_path):
    from hydrahive.agents import config as agent_config
    from hydrahive.agents._paths import workspace_for
    a = agent_config.create(agent_type="project", name="Auftraggeber", llm_model="m", owner="testuser",
                            temperature=0.7, max_tokens=1000, thinking_budget=0, project_id="p-rep")
    try:
        d = rep.reports_dir_for_caller(f"hydrahive/{a['id']}")
        assert d == workspace_for(a) / ".hydrahive" / "reports"
        out = rep.split_reply("y" * 5000, key="h9", limit=100, directory=d)
        assert str(d) in out and (d / "h9.md").read_text() == "y" * 5000
    finally:
        agent_config.delete(a["id"])
    assert rep.reports_dir_for_caller("hydrahive") is None
    assert rep.reports_dir_for_caller("hydrahive/../../x") is None


def test_auftrag_enthaelt_antwortformat():
    from hydrahive.agentlink.protocol import ContextBlock, State, TaskBlock
    from hydrahive.runner.handoff_receiver import _build_user_input
    text = _build_user_input(State(agent_id="x", task=TaskBlock(type="review", description="prüf"),
                                   context=ContextBlock()))
    assert "## Ergebnis" in text and "## Offene Punkte" in text
