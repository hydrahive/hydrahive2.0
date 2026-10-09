"""Recall C (Kartensuche) hält die Wissensräume ein (Task ddb1ff35, knowledge-spaces.md §2.3).

Vorher filterte search_cards nur nach Nutzer – ein Projekt-Agent bekam per Ähnlichkeit auch Karten
anderer Agenten, z. B. aus Buddy-Sitzungen mit Gesundheits-Werkzeugen. Jetzt: eigene Karten immer,
fremde nur über die Sicht des Agenten (_mirror_scope.where).
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

from hydrahive.db._mirror_cards_search import card_filter, search_cards
from hydrahive.db._mirror_levels import hidden_tools
from hydrahive.db._mirror_scope import Scope, scope_for


def _project_scope():
    return scope_for({"type": "project"}, username="till", project_id="P1")


# ── Filter-Bausteine ──────────────────────────────────────────────────────────

def test_eigene_karten_oder_fremde_nur_in_der_sicht():
    cond, params, nxt = card_filter(_project_scope(), "A1", 3)
    assert cond.startswith("c.username = $3 AND (c.agent_id = $")
    assert "EXISTS (SELECT 1 FROM events e WHERE e.session_id = c.session_id" in cond
    assert params[0] == "till" and params[-1] == "A1" and ["P1"] in params
    assert nxt == 3 + len(params)


def test_alle_sichtbedingungen_muessen_gleichzeitig_gelten():
    from hydrahive.db._mirror_scope import where
    conds, _, _ = where(_project_scope(), 4, alias="e")
    cond, _, _ = card_filter(_project_scope(), "A1", 3)
    assert len(conds) >= 3 and f"c.session_id AND {' AND '.join(conds)})" in cond
    assert " OR " not in cond.split("EXISTS", 1)[1]        # Projekt UND Nutzer UND Stufe – nie entweder/oder


def test_projekt_agent_sieht_fremde_nur_bis_normal():
    cond, params, _ = card_filter(_project_scope(), "A1", 3)
    assert hidden_tools("normal") in params            # Gesundheit/Privat-Sitzungen ausgeblendet
    assert "e.project_id = ANY(" in cond


def test_buddy_sieht_alles_des_nutzers_ohne_stufensperre():
    sc = scope_for({"type": "master"}, username="till", project_id=None)
    cond, params, _ = card_filter(sc, "B1", 3)
    assert "e.project_id" not in cond and "tool_name" not in cond
    assert params == ["till", "till", "B1"]


def test_ohne_projekt_nur_eigene_karten():
    sc = scope_for({"type": "specialist"}, username="till", project_id=None)
    cond, params, _ = card_filter(sc, "S1", 3)
    assert cond == "c.username = $3 AND (c.agent_id = $4 OR FALSE)" and params == ["till", "S1"]


def test_ohne_nutzer_nie_treffer():
    assert card_filter(Scope(username=""), "A1", 3)[0] == "FALSE"


def test_ohne_agent_nur_ueber_die_sicht():
    cond, _, _ = card_filter(_project_scope(), None, 3)
    assert "c.agent_id" not in cond and "EXISTS" in cond


def test_werte_nur_als_parameter():
    evil = "x' OR '1'='1"
    cond, params, _ = card_filter(Scope(username=evil, projects=(evil,)), evil, 3)
    assert evil not in cond and evil in params


# ── search_cards: der echte SQL-Aufruf ────────────────────────────────────────

class _Tx:
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False


class _Conn:
    def __init__(self, seen): self.seen = seen; self.executed = []
    def transaction(self): return _Tx()
    async def execute(self, sql): self.executed.append(sql)
    async def fetch(self, sql, *args):
        self.seen.append((sql, args, list(self.executed)))
        return []


class _Pool:
    def __init__(self, seen): self.seen = seen
    def acquire(self):
        conn = _Conn(self.seen)

        class _Ctx:
            async def __aenter__(self): return conn
            async def __aexit__(self, *a): return False
        return _Ctx()


def _run(**kw):
    seen: list = []

    async def fake_embed(*a, **k):
        return [0.1, 0.2]
    with patch("hydrahive.db._mirror_search._pool", return_value=_Pool(seen)), \
         patch("hydrahive.llm._config.load_config", return_value={"embed_model": "m"}), \
         patch("hydrahive.llm.embed.aembed", side_effect=fake_embed):
        asyncio.run(search_cards("wie war das mit dem deploy", 3, **kw))
    return seen


def test_suche_nutzt_den_sichtfilter():
    seen = _run(username="till", agent_id="A1", scope=_project_scope())
    sql, args, pre = seen[0]
    assert pre == ["SET LOCAL hnsw.iterative_scan = relaxed_order"]   # nur in der Transaktion, kein SET global
    assert "FROM cards c WHERE embedding IS NOT NULL AND c.username = $3 AND (c.agent_id = $" in sql
    assert args[1] == 3 and args[2] == "till" and args[-1] == "A1"
    import re
    used = {int(n) for n in re.findall(r"\$(\d+)", sql)}
    assert used == set(range(1, len(args) + 1))            # jeder Platzhalter hat genau einen Wert


def test_ohne_scope_nur_eigene_karten_nie_ungefiltert():
    sql, args, _ = _run(username="till", agent_id="A1")[0]
    assert "OR FALSE" in sql and args[2:] == ("till", "A1")
    assert _run(username="till") == []                     # weder Scope noch Agent → keine Abfrage


def test_scope_eines_anderen_nutzers_wird_abgelehnt():
    sc = scope_for({"type": "master"}, username="bibi", project_id=None)
    assert _run(username="till", agent_id="A1", scope=sc) == []


def test_runner_uebergibt_agent_und_scope():
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "src/hydrahive/runner/runner.py"
    code = src.read_text(encoding="utf-8")
    assert "scope_for(agent, username=session.user_id, project_id=active_project_id)" in code
    assert 'agent_id=agent["id"], scope=recall_scope' in code
