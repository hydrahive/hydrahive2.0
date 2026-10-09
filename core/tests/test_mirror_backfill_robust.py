"""Embedding-Nachtrag hängt nicht mehr an einem zu langen Text (Task 36caf245).

Vorher: Kürzung nach Zeichen (24.000) → ein tool_call mit 9.644 Tokens > 8.192 → OpenAI lehnte das ganze 32er-Paket
ab → 0 gespeichert → Abbruch; nächster Start wieder dieselben ältesten 200 → dauerhaft festgefahren.
"""
from __future__ import annotations

import asyncio

from hydrahive.db import _embed_clip
from hydrahive.db import _mirror_embed as me


# ── Kürzung nach Tokens ───────────────────────────────────────────────────────

def test_kurzer_text_bleibt_unveraendert():
    assert _embed_clip.clip_for_embedding("hallo welt") == "hallo welt"


def test_langer_text_wird_auf_token_limit_gekuerzt():
    enc = _embed_clip._encoder()
    text = "ä€x9 " * 20_000                           # dicht: viele Tokens je Zeichen
    out = _embed_clip.clip_for_embedding(text)
    assert len(enc.encode(out, disallowed_special=())) <= _embed_clip.MAX_TOKENS
    assert text.startswith(out[:100])


def test_24000_zeichen_koennen_ueber_dem_limit_liegen_und_werden_gekuerzt():
    enc = _embed_clip._encoder()
    text = ('{"command": "' + "a\\nb=1;" * 4000)[:24_000]
    assert len(enc.encode(text, disallowed_special=())) > 8192          # genau der Fall vom 09.10.
    assert len(enc.encode(_embed_clip.clip_for_embedding(text), disallowed_special=())) <= 8000


def test_sonder_tokens_im_text_werfen_nicht():
    assert "<|endoftext|>" in _embed_clip.clip_for_embedding("x <|endoftext|> y" * 3000)


def test_ohne_tokenizer_vorsichtig_nach_zeichen(monkeypatch):
    monkeypatch.setattr(_embed_clip, "_encoder", lambda: None)
    assert len(_embed_clip.clip_for_embedding("a" * 50_000)) == _embed_clip.FALLBACK_CHARS


def test_embed_text_nutzt_die_token_kuerzung():
    out = me.embed_text({"tool_name": "Bash", "tool_input": None, "text": "ä€x9 " * 20_000})
    enc = _embed_clip._encoder()
    assert out.startswith("Bash: ") and len(enc.encode(out, disallowed_special=())) <= 8000


# ── Paket-Fehler: einzeln nachversuchen ──────────────────────────────────────

def _fake_embed(bad: set[str], calls: list):
    async def aembed_batch(texts, model, embed_type="db", _retry=3):
        calls.append(list(texts))
        if any(t in bad for t in texts):
            return [None] * len(texts)                       # API lehnt das ganze Paket ab
        return [[0.1, 0.2] for _ in texts]
    return aembed_batch


def _run_sub(monkeypatch, texts, bad):
    calls: list = []
    stored: list = []

    async def store(pool, ids, vecs, model):
        stored.extend(i for i, v in zip(ids, vecs) if v is not None)
        return sum(v is not None for v in vecs)
    monkeypatch.setattr("hydrahive.llm.embed.aembed_batch", _fake_embed(bad, calls))
    monkeypatch.setattr(me, "_store_batch", store)
    n = asyncio.run(me._embed_sub(object(), [(f"id{i}", t) for i, t in enumerate(texts)], "m"))
    return n, stored, calls


def test_ein_kaputter_text_blockiert_das_paket_nicht_mehr(monkeypatch):
    n, stored, calls = _run_sub(monkeypatch, ["a", "b", "BAD", "c"], {"BAD"})
    assert n == 3 and stored == ["id0", "id1", "id3"]
    assert calls[0] == ["a", "b", "BAD", "c"] and len(calls) == 5             # 1 Paket + 4 einzeln


def test_gesundes_paket_nur_ein_aufruf(monkeypatch):
    n, _, calls = _run_sub(monkeypatch, ["a", "b"], set())
    assert n == 2 and len(calls) == 1


def test_einzelner_kaputter_text_kein_doppelter_versuch(monkeypatch):
    n, _, calls = _run_sub(monkeypatch, ["BAD"], {"BAD"})
    assert n == 0 and len(calls) == 1


# ── Schleife: blättert vorwärts, bleibt nicht hängen ─────────────────────────

class _Conn:
    def __init__(self, rows):
        self.rows, self.args = rows, []

    async def fetch(self, sql, limit, after_ts, after_id):
        self.args.append((after_ts, after_id))
        rest = [r for r in self.rows if after_ts is None or (r["created_at"], r["id"]) > (after_ts, after_id)]
        return rest[:limit]


class _Pool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        conn = self.conn

        class _C:
            async def __aenter__(self): return conn
            async def __aexit__(self, *a): return False
        return _C()


def test_schleife_blaettert_weiter_statt_dieselben_zu_wiederholen(monkeypatch):
    rows = [{"id": f"e{i:02}", "tool_name": None, "created_at": i // 3, "content": "BAD" if i == 0 else f"t{i}"}
            for i in range(9)]
    conn = _Conn(rows)
    stored: list = []

    async def store(pool, ids, vecs, model):
        stored.extend(i for i, v in zip(ids, vecs) if v is not None)
        return sum(v is not None for v in vecs)
    monkeypatch.setattr("hydrahive.llm.embed.aembed_batch", _fake_embed({"BAD"}, []))
    monkeypatch.setattr(me, "_store_batch", store)
    total = asyncio.run(me.backfill_loop(_Pool(conn), "m", batch_size=4, sleep_between=0))
    assert total == 8 and stored == [f"e{i:02}" for i in range(1, 9)]          # alle außer dem kaputten
    assert conn.args[0] == (None, "") and conn.args[1] == (1, "e03") and conn.args[2] == (2, "e07")


def test_schleife_kuerzt_lange_texte_vor_dem_senden(monkeypatch):
    enc = _embed_clip._encoder()
    rows = [{"id": "e1", "tool_name": "Bash", "created_at": 1, "content": "ä€x9 " * 20_000}]
    sent: list = []

    async def aembed_batch(texts, model, embed_type="db", _retry=3):
        sent.extend(texts)
        return [[0.1] for _ in texts]

    async def store(pool, ids, vecs, model):
        return len(ids)
    monkeypatch.setattr("hydrahive.llm.embed.aembed_batch", aembed_batch)
    monkeypatch.setattr(me, "_store_batch", store)
    asyncio.run(me.backfill_loop(_Pool(_Conn(rows)), "m", batch_size=4, sleep_between=0))
    assert sent and sent[0].startswith("Bash: ")
    assert len(enc.encode(sent[0], disallowed_special=())) <= _embed_clip.MAX_TOKENS


def test_sql_blaettert_nach_zeit_und_id():
    assert "(created_at, id) > ($2::timestamptz, $3::text)" in me._BACKFILL_SQL
    assert "ORDER BY created_at, id" in me._BACKFILL_SQL
