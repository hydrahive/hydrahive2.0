"""G2: datamining_search über den Gesamtindex event_docs (docs/specs/datamining-gesamtindex.md §3.3).

Gemessen 10.10. (echter Werkzeug-Code, Messrahmen, Daten bis 09.10. 16:00): echte Fragen alt 0 % Treffer@5
(9 von 10 ohne Treffer) → neu 40 % / MRR 0,275, Median 22 ms, max 288 ms.
"""
from __future__ import annotations

import asyncio
import re

import pytest

from hydrahive.db import _mirror_textsearch as ts
from hydrahive.db._mirror_scope import Scope
from hydrahive.db._mirror_search import _dt, _text_search
from hydrahive.db._mirror_words import split_words


class _Conn:
    def __init__(self):
        self.calls = []

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        return []


def _run(q, **kw):
    conn = _Conn()
    args = dict(event_type=None, agent_name=None, username="till", from_date=None, to_date=None, limit=20)
    args.update(kw)
    asyncio.run(_text_search(conn, q, args["event_type"], args["agent_name"], args["username"], args["from_date"],
                             args["to_date"], args["limit"], kw.get("scope")))
    return conn.calls[0]


# ── Zerlegung ─────────────────────────────────────────────────────────────────

def test_satz_wird_in_woerter_zerlegt():
    assert split_words("Discord Handbuch Modul") == ["handbuch", "discord", "modul"]


def test_fuellwoerter_kurze_und_dubletten_fallen_weg():
    assert split_words("wie war das mit DEM Teddy, teddy?") == ["teddy"]


def test_punkte_und_bindestriche_bleiben():
    assert split_words("hydratest update.sh branch") == ["hydratest", "update.sh", "branch"]


def test_hoechstens_sechs_laengste():
    ws = split_words("aaa bbbb ccccc dddddd eeeeeee ffffffff ggggggggg")
    assert ws == ["ggggggggg", "ffffffff", "eeeeeee", "dddddd", "ccccc", "bbbb"]


# ── SQL ───────────────────────────────────────────────────────────────────────

def test_sucht_im_index_mit_rang_sortierung():
    """Ohne ORDER BY rank nutzte Postgres den GIN-Index nicht (gemessen: 1,1 s statt 2–25 ms)."""
    sql, args = _run("Teddybär Milch")
    assert "FROM event_docs d, q" in sql and "d.tsv @@ q.q" in sql
    assert "ORDER BY rank DESC, d.created_at DESC" in sql
    assert ts.RANK == "ts_rank(d.tsv, q.q, 1)"
    assert "ILIKE" not in sql


def test_woerter_nur_als_parameter_je_wort_plainto_tsquery():
    sql, args = _run("teddybär'); DROP TABLE events; -- milch")
    assert "DROP" not in sql and "teddybär" not in sql
    n = sql.count("plainto_tsquery('simple', $")
    assert n == len(split_words("teddybär'); DROP TABLE events; -- milch"))
    assert " || plainto_tsquery" in sql                      # ODER-Verknüpfung
    assert "to_tsquery(" not in sql.replace("plainto_tsquery(", "")


def test_wort_parameter_stehen_vorne_in_reihenfolge():
    sql, args = _run("datenbank claude erste")
    assert list(args[:3]) == ["datenbank", "claude", "erste"]
    assert args[3] == "till" and args[-1] == 20


def test_kurze_anfrage_ohne_wort_ab_drei_zeichen_sucht_trotzdem_im_index():
    sql, args = _run("KI")
    assert "event_docs" in sql and args[0] == "KI"


def test_leere_anfrage_listet_neueste_wie_bisher():
    """Zahnfee holt mit q='' die Ereignisse eines Zeitraums – das bleibt nach Datum."""
    sql, args = _run("", from_date="2026-10-01")
    assert "FROM events" in sql and "event_docs" not in sql
    assert "ORDER BY created_at DESC" in sql
    assert args[0] == "till" and args[1] == _dt("2026-10-01")


def test_datumsfilter_wirken_auf_die_dokumente():
    sql, args = _run("teddy", from_date="2026-01-01", to_date="2026-10-09")
    assert re.search(r"d\.created_at >= \$\d+", sql) and re.search(r"d\.created_at <= \$\d+", sql)
    assert _dt("2026-01-01") in args and _dt("2026-10-09") in args


def test_typ_filter_am_dokument_ohne_join_fuer_werkzeug_ergebnisse_und_im_ausschnitt():
    sql, args = _run("teddy", event_type="tool_call")
    n = args.index("tool_call") + 1
    assert f"WHEN d.doc_id LIKE 'r:%' THEN ${n} = 'tool_result'" in sql
    assert f"EXISTS (SELECT 1 FROM events e WHERE e.id = d.doc_id AND e.event_type = ${n})" in sql
    assert sql.count(f"e.event_type = ${n}") == 2            # Dokument + Ausschnitt


def test_agent_filter_ueber_sitzungen_einmal_und_im_ausschnitt():
    sql, args = _run("teddy", agent_name="Buddy")
    n = args.index("Buddy") + 1
    assert (f"d.session_id = ANY(ARRAY(SELECT DISTINCT a.session_id FROM events a WHERE a.agent_name = ${n} "
            f"AND a.username = ${n + 1}))") in sql
    assert args[n] == "till"                                 # Nutzer begrenzt die Sitzungsliste
    assert f"e.agent_name = ${n}" in sql                     # Ausschnitt


def test_agent_filter_ohne_nutzer():
    sql, args = _run("teddy", agent_name="Buddy", username=None)
    n = args.index("Buddy") + 1
    assert f"WHERE a.agent_name = ${n}))" in sql


def test_ohne_typ_agent_keine_zusatzpruefung():
    sql, _ = _run("teddy")
    assert "EXISTS (" not in sql and "a.agent_name" not in sql


def test_sicht_des_agenten_gilt_im_index():
    sc = Scope(username="till", scope="project", projects=("P1",), max_level="normal")
    sql, args = _run("teddy", scope=sc)
    assert "d.username = $" in sql and "d.project_id = ANY($" in sql
    assert "d.session_id <> ALL(ARRAY(SELECT DISTINCT s.session_id FROM events s" in sql
    assert ["P1"] in [a for a in args if isinstance(a, list)]


def test_sicht_ohne_projekt_liefert_nichts():
    sql, _ = _run("teddy", scope=Scope(username="till", scope="project", projects=()))
    assert "FALSE" in sql


def test_ausschnitt_aus_passendem_stueck_um_die_fundstelle():
    sql, _ = _run("teddy")
    assert "CROSS JOIN LATERAL" in sql and "LIMIT 1) ev" in sql
    assert "ts_headline('simple', ev.body, q.q" in sql
    assert "e.tool_use_id = substr(top.doc_id, 3)" in sql and "e.id = top.doc_id" in sql
    # zuerst das Stück, in dem das Wort vorkommt
    assert sql.index("@@ q.q) DESC") < sql.index("(e.id LIKE 'full:%')")


def test_antwortformat_bleibt():
    sql, _ = _run("teddy")
    for col in ("ev.id", "top.session_id", "ev.username", "ev.agent_name", "ev.event_type", "ev.created_at",
                "ev.tool_name", "ev.is_error", "AS snippet", "AS rank"):
        assert col in sql


def test_limit_gilt_fuer_dokumente():
    sql, args = _run("teddy", limit=7)
    assert args[-1] == 7
    assert re.search(r"LIMIT \$(\d+)\)", sql).group(1) == str(len(args))


def test_gruppen_sicht_gilt_auch_im_index():
    """Wissensräume (#534): Gruppenmitglieder nur Projekt-Sitzungen, keine Master-Agenten, höchstens normal."""
    sc = Scope(username="till", scope="project", projects=("P1",), max_level="normal",
               group_users=("anna",), master_agents=("M1",))
    sql, args = _run("teddy", scope=sc)
    assert "d.username = ANY($" in sql and "d.project_id IS NOT NULL" in sql
    assert "d.agent_id IS NOT NULL" in sql and "d.agent_id <> ALL($" in sql
    assert ["anna"] in [a for a in args if isinstance(a, list)] and ["M1"] in [a for a in args if isinstance(a, list)]


def test_nutzerfilter_begrenzt_die_dokumente():
    """Oberfläche: Nicht-Admins sehen nur eigene Ereignisse (scoped_username) – hier ohne Agenten-Sicht."""
    sql, args = _run("teddy", username="anna")
    n = args.index("anna") + 1
    assert f"d.username = ${n}" in sql.split("FROM top, q")[0]


def test_ohne_nutzer_kein_nutzerfilter():
    sql, args = _run("teddy", username=None)
    assert "d.username" not in sql and "till" not in args
