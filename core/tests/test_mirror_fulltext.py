"""Volle Werkzeug-Ausgaben in den Datamining-Index (docs/specs/datamining-volltext-werkzeuge.md).

Vorher stand nur der Teil bis zur Grenze des Agenten (tool_result_max_chars) im Index – gemessen 2.305 Aufrufe,
die abgeschnittenen Teile waren für die Suche unsichtbar.
"""
from __future__ import annotations

import asyncio
import json

from hydrahive.db import _mirror_fulltext as ft
from hydrahive.db import _mirror_fulltext_backfill as fb

BASE = {"message_id": "m1", "session_id": "s1", "block_index": 2, "username": "till", "agent_id": "a1",
        "agent_name": "A", "project_id": "p1", "created_at": "2026-10-09T10:00:00+00:00"}


def _stored(output, success=True, error=None):
    return json.dumps({"success": success, "output": output, "error": error, "metadata": {}})


# ── Rest-Text ────────────────────────────────────────────────────────────────

def test_rest_ist_genau_der_abgeschnittene_teil():
    full = "a" * 100 + "REST"
    assert ft.rest_text(full, 100) == "REST"


def test_kein_rest_wenn_nicht_laenger_als_grenze():
    assert ft.rest_text("kurz", 100) == "" and ft.rest_text("x", 0) == "" and ft.rest_text("", 5) == ""


def test_obergrenze_anfang_und_ende_bleiben():
    full = "A" * 1000 + "M" * 500_000 + "Z" * 1000
    rest = ft.rest_text(full, 1000)
    assert 1000 + len(rest) <= ft.MAX_CHARS + 60
    assert rest.startswith("M") and rest.endswith("Z" * 1000) and "Zeichen ausgelassen" in rest


def test_grenze_ueber_obergrenze_kein_rest():
    assert ft.rest_text("x" * 300_000, 250_000) == ""


# ── Text wie der Agent ihn sah ───────────────────────────────────────────────

def test_agent_text_ist_to_llm_der_gespeicherten_fassung():
    assert ft.agent_text(_stored("hallo")) == "hallo"
    assert ft.agent_text(_stored({"k": 1})) == json.dumps({"k": 1}, indent=2, ensure_ascii=False)
    assert ft.agent_text(_stored(None, success=False, error="kaputt")) == "FEHLER: kaputt"


def test_agent_text_kein_json_bleibt_wie_es_ist():
    assert ft.agent_text("nur text") == "nur text" and ft.agent_text("") == ""


# ── Ereignisse ───────────────────────────────────────────────────────────────

def _call(output, limit, **kw):
    return {"id": "tc1", "tool_name": "shell_exec", "tool_use_id": "tu1", "result": _stored(output),
            "truncate_limit_chars": limit, "status": "success", **kw}


def test_stuecke_ids_und_felder():
    evs = ft.build_events(_call("a" * 10 + "b" * 7000, 10), BASE)
    assert [e["id"] for e in evs] == ["full:tc1:0", "full:tc1:1", "full:tc1:2"]
    assert [len(e["tool_output"]) for e in evs] == [3000, 3000, 1000]
    assert all(e["event_type"] == "tool_result" and e["tool_use_id"] == "tu1" and e["session_id"] == "s1"
               and e["project_id"] == "p1" and e["chunk_total"] == 3 for e in evs)


def test_secrets_im_rest_werden_geschwaerzt():
    token = "ghp_" + "A1b2C3d4E5" * 4
    evs = ft.build_events(_call("x" * 10 + f" token={token} ende", 10), BASE)
    joined = "".join(e["tool_output"] for e in evs)
    assert token not in joined and "[REDACTED]" in joined


def test_fehlerstatus_bleibt_erhalten():
    evs = ft.build_events(_call("x" * 20, 5, status="error"), BASE)
    assert evs and all(e["is_error"] for e in evs)


def test_ohne_rest_keine_ereignisse():
    assert ft.build_events(_call("kurz", 100), BASE) == []


# ── Nachtrag ─────────────────────────────────────────────────────────────────

class _Conn:
    def __init__(self, base_rows, existing):
        self.base_rows, self.existing, self.inserted = base_rows, existing, []

    async def fetch(self, sql, ids):
        return [r for r in self.base_rows if r["tool_use_id"] in ids]

    async def fetchval(self, sql, ids):
        return sum(1 for i in ids if i in self.existing)

    async def executemany(self, sql, rows):
        assert "ON CONFLICT (id) DO NOTHING" in sql
        for r in rows:
            if r[0] not in self.existing:
                self.existing.add(r[0])
                self.inserted.append(r)


class _Pool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        conn = self.conn

        class _C:
            async def __aenter__(self): return conn
            async def __aexit__(self, *a): return False
        return _C()


def _run(monkeypatch, calls, base_rows, existing=None):
    pages = [calls[i:i + fb.PAGE] for i in range(0, len(calls), fb.PAGE)] + [[]]
    monkeypatch.setattr(fb, "_calls", lambda after, limit: [c for c in calls if c["id"] > after][:limit])
    conn = _Conn(base_rows, existing if existing is not None else set())
    stats = asyncio.run(fb.backfill_fulltext(_Pool(conn)))
    return stats, conn, pages


def _sql_call(i, sess="s1"):
    return {**_call("x" * 10 + "R" * 4000, 10), "id": f"tc{i:03}", "tool_use_id": f"tu{i:03}", "session_id": sess}


def test_nachtrag_schreibt_rest_ohne_embedding(monkeypatch):
    calls = [_sql_call(1)]
    stats, conn, _ = _run(monkeypatch, calls, [{**BASE, "tool_use_id": "tu001"}])
    assert stats == {"calls": 1, "no_base": 0, "written": 2}
    assert {r[16] for r in conn.inserted} == {ft.SKIP_EMBED}
    assert {r[1] for r in conn.inserted} == {"m1"} and {r[2] for r in conn.inserted} == {"s1"}


def test_zweiter_lauf_schreibt_nichts(monkeypatch):
    calls = [_sql_call(1)]
    base = [{**BASE, "tool_use_id": "tu001"}]
    existing: set = set()
    _run(monkeypatch, calls, base, existing)
    stats, conn, _ = _run(monkeypatch, calls, base, existing)
    assert stats["written"] == 0 and conn.inserted == []


def test_ohne_original_oder_andere_sitzung_wird_uebersprungen(monkeypatch):
    calls = [_sql_call(1), _sql_call(2, sess="fremd")]
    stats, conn, _ = _run(monkeypatch, calls, [{**BASE, "tool_use_id": "tu002"}])
    assert stats["no_base"] == 2 and conn.inserted == []


def test_blaettert_ueber_mehrere_seiten(monkeypatch):
    calls = [_sql_call(i) for i in range(fb.PAGE + 7)]
    base = [{**BASE, "tool_use_id": c["tool_use_id"]} for c in calls]
    stats, _, _ = _run(monkeypatch, calls, base)
    assert stats["calls"] == fb.PAGE + 7 and stats["written"] == 2 * (fb.PAGE + 7)


def test_embedding_nachtrag_und_reset_lassen_skip_stuecke_in_ruhe():
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "src/hydrahive/db"
    assert "NOT LIKE 'skip:%'" in (src / "_mirror_embed.py").read_text()
    assert (src / "mirror.py").read_text().count("NOT LIKE 'skip:%'") == 2
    assert "NOT LIKE 'skip:%'" in (src / "_mirror_search.py").read_text()
