"""Gesamtindex event_docs (docs/specs/datamining-gesamtindex.md, G1).

Vorher: Suche nur über ein Fenster der neuesten Einträge, Wörter über 3.000er-Stückgrenzen unauffindbar
(49 % der Grenzen mitten im Wort). Jetzt: je Werkzeug-Ergebnis ein Dokument über alle Stücke, gepflegt beim Spiegeln.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from hydrahive.db import _mirror_docs as d
from hydrahive.db import _mirror_docs_sync as s

SRC = Path(__file__).resolve().parents[1] / "src/hydrahive"


# ── Dokument-Schlüssel ───────────────────────────────────────────────────────

def test_werkzeug_ergebnis_ist_ein_dokument_ueber_alle_stuecke():
    a = d.doc_key({"id": "m:1:0", "event_type": "tool_result", "tool_use_id": "tu9"})
    b = d.doc_key({"id": "m:1:1", "event_type": "tool_result", "tool_use_id": "tu9"})
    c = d.doc_key({"id": "full:tc:0", "event_type": "tool_result", "tool_use_id": "tu9"})
    assert a == b == c == "r:tu9"


def test_alles_andere_je_ereignis():
    assert d.doc_key({"id": "m:0:0", "event_type": "user_input"}) == "m:0:0"
    assert d.doc_key({"id": "m:2:0", "event_type": "tool_call", "tool_use_id": "tu9"}) == "m:2:0"
    assert d.doc_key({"id": "x", "event_type": "tool_result", "tool_use_id": None}) == "x"


def test_python_schluessel_gleich_sql_schluessel():
    sql = d.DOC_KEY.format(a="e")
    assert "e.event_type = 'tool_result' AND e.tool_use_id IS NOT NULL" in sql and "'r:' || e.tool_use_id" in sql


# ── SQL ──────────────────────────────────────────────────────────────────────

def test_dokument_text_in_stueck_reihenfolge_volltext_stuecke_hinten():
    assert "ORDER BY (e.id LIKE 'full:%'), e.message_id, e.block_index, e.chunk_index, e.id" in d.REFRESH_SQL


def test_simple_und_obergrenze():
    assert "to_tsvector('simple', left(" in d.REFRESH_SQL and f"{d.MAX_DOC_CHARS}))" in d.REFRESH_SQL
    assert d.MAX_DOC_CHARS <= 1_000_000


def test_upsert_aktualisiert_auch_sicht_felder():
    for col in ("session_id", "username", "agent_id", "project_id", "tsv", "built_at"):
        assert re.search(rf"\b{col} = (EXCLUDED\.{col}|now\(\))", d.REFRESH_SQL), col


def test_refresh_nutzt_indizes_statt_ausdruck_auf_events():
    assert "e.tool_use_id = ANY($1::text[]) AND e.event_type = 'tool_result'" in d.REFRESH_SQL
    assert "e.id = ANY($2::text[])" in d.REFRESH_SQL
    assert "CREATE INDEX IF NOT EXISTS events_tool_use_id ON events (tool_use_id)" in d.DDL


def test_ddl_nur_additiv():
    assert "ALTER TABLE" not in d.DDL and "DROP" not in d.DDL
    assert all(line.strip().startswith(("CREATE TABLE IF NOT EXISTS", "CREATE INDEX IF NOT EXISTS", ")", ""))
               or line.startswith("  ") for line in d.DDL.splitlines())


# ── refresh_docs ─────────────────────────────────────────────────────────────

class _Conn:
    def __init__(self):
        self.calls = []

    async def execute(self, sql, *args, **kw):
        self.calls.append((sql, args))


def test_refresh_trennt_werkzeug_und_ereignis_schluessel():
    c = _Conn()
    n = asyncio.run(d.refresh_docs(c, ["r:tu1", "m:0:0", "r:tu1", None, "r:tu2"]))
    assert n == 3
    (sql1, a1), (sql2, a2) = c.calls
    assert sql1 == d.REFRESH_SQL and a1 == (["tu1", "tu2"], ["m:0:0"])
    assert sql2 == d.PRUNE_SQL and a2 == (["m:0:0", "r:tu1", "r:tu2"],)


def test_refresh_ohne_schluessel_keine_abfrage():
    c = _Conn()
    assert asyncio.run(d.refresh_docs(c, [])) == 0 and c.calls == []


class _Pool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        conn = self.conn

        class _C:
            async def __aenter__(self): return conn
            async def __aexit__(self, *a): return False
        return _C()


def test_pflege_wirft_nie(caplog):
    class _Bad:
        async def execute(self, *a, **k):
            raise RuntimeError("db weg")
    asyncio.run(d.refresh_for_events(_Pool(_Bad()), [{"id": "a", "event_type": "user_input"}]))
    assert any("event_docs" in r.message for r in caplog.records)


def test_pflege_ohne_pool_oder_ereignisse_nichts():
    asyncio.run(d.refresh_for_events(None, [{"id": "a"}]))
    c = _Conn()
    asyncio.run(d.refresh_for_events(_Pool(c), []))
    assert c.calls == []


# ── Nachhol-Lauf ─────────────────────────────────────────────────────────────

class _SyncConn:
    def __init__(self, has_docs, pending_pages):
        self.has_docs, self.pages, self.log = has_docs, list(pending_pages), []

    async def fetchval(self, sql, *a, **k):
        return self.has_docs

    async def execute(self, sql, *a, **k):
        self.log.append(("exec", sql.strip()[:30], a))

    async def fetch(self, sql, limit, **k):
        page = self.pages.pop(0) if self.pages else []
        return [{"k": x} for x in page]


def test_leerer_index_wird_voll_aufgebaut_dann_nichts_mehr(monkeypatch):
    c = _SyncConn(False, [[]])
    st = asyncio.run(s.sync_docs(_Pool(c)))
    assert st == {"full_build": True, "refreshed": 0, "rounds": 0}
    assert c.log[0][1].startswith("INSERT INTO event_docs")


def test_fehlende_und_veraltete_werden_in_runden_nachgeholt(monkeypatch):
    monkeypatch.setattr(s, "BATCH", 2)
    c = _SyncConn(True, [["r:a", "b"], ["r:c", "d"], ["e"]])
    st = asyncio.run(s.sync_docs(_Pool(c)))
    assert st == {"full_build": False, "refreshed": 5, "rounds": 3}


def test_pending_erkennt_fehlend_und_veraltet():
    assert "d.doc_id IS NULL OR e.mirrored_at > d.built_at" in s._PENDING
    assert "ON CONFLICT (doc_id) DO NOTHING" in s._FULL_BUILD


def test_lange_laeufe_mit_eigenem_timeout():
    for name in ("_FULL_BUILD", "_PENDING", "_COVERAGE"):
        assert name in Path(s.__file__).read_text()
    assert s.BUILD_TIMEOUT >= 600


# ── angebunden an alle Schreibpfade ──────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "db/_mirror_writes.py", "db/_mirror_fulltext_backfill.py", "api/routes/_datamining_rechunk.py",
    "api/routes/datamining.py", "api/routes/datamining_issues.py", "db/mirror_import_git.py",
    "db/mirror_import_logs.py", "db/mirror_import_shell.py", "db/mirror_import_sqlite.py",
])
def test_jeder_schreibpfad_pflegt_den_index(path):
    code = (SRC / path).read_text()
    assert "INSERT INTO events" in code and re.search(r"refresh_(docs|for_events)\(", code)


def test_keine_weiteren_schreibpfade_ohne_pflege():
    writers = [p for p in SRC.rglob("*.py") if "INSERT INTO events" in p.read_text()]
    assert all(re.search(r"refresh_(docs|for_events)\(", p.read_text()) for p in writers), \
        [str(p.relative_to(SRC)) for p in writers if not re.search(r"refresh_(docs|for_events)\(", p.read_text())]


def test_write_message_pflegt_nach_dem_insert(monkeypatch):
    from hydrahive.db import _mirror_writes as w
    seen = []

    async def fake_refresh(pool, events):
        seen.append([e["id"] for e in events])
    monkeypatch.setattr(w, "refresh_for_events", fake_refresh)
    monkeypatch.setattr(w, "queue_embed", lambda *a: None)
    monkeypatch.setattr(w, "explode", lambda m, s: [{"id": "m:0:0", "message_id": "m", "session_id": "s",
        "block_index": 0, "chunk_index": 0, "chunk_total": 1, "username": "u", "agent_id": "a", "agent_name": "A",
        "project_id": None, "event_type": "user_input", "text": "hi", "created_at": "2026-10-10T00:00:00+00:00"}])

    class _C:
        async def executemany(self, *a, **k): pass
    asyncio.run(w.write_message(_Pool(_C()), object(), object()))
    assert seen == [["m:0:0"]]


def test_init_legt_index_an_und_faellt_nicht_um():
    code = (SRC / "db/mirror.py").read_text()
    i = code.index("_ensure_docs(conn)")
    assert "try:" in code[i - 200:i] and "except Exception" in code[i:i + 200]


def test_naechtlicher_lauf_beides_und_wirft_nie(monkeypatch):
    from hydrahive.zahnfee import scheduler as sch
    order = []

    async def ok_full(pool):
        order.append("full")

    async def bad_sync(pool):
        order.append("sync")
        raise RuntimeError("x")
    monkeypatch.setattr("hydrahive.db._mirror_fulltext_backfill.backfill_fulltext", ok_full)
    monkeypatch.setattr("hydrahive.db._mirror_docs_sync.sync_docs", bad_sync)
    asyncio.run(sch._nightly_index(object()))
    assert order == ["full", "sync"]
