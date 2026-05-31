"""Lokal testbare Oberfläche von Task 3 (Card-Store).

Die echten PG-Operationen (upsert/get/wipe gegen den Mirror) testet Till nach
Deploy — hier nur Import-Smoke + DDL-/Signatur-Checks + der reine Vektor-Helfer,
alles ohne PG.
"""
from __future__ import annotations

import inspect


def test_card_store_imports():
    from hydrahive.db._mirror_cards import get_card, upsert_card, wipe_cards
    assert callable(upsert_card) and callable(get_card) and callable(wipe_cards)


def test_cards_table_in_ddl():
    from hydrahive.db._mirror_ddl import DDL_TABLES
    assert "CREATE TABLE IF NOT EXISTS cards" in DDL_TABLES
    # recompute-safe braucht card_id als Konflikt-Anker (ON CONFLICT card_id)
    assert "card_id             TEXT PRIMARY KEY" in DDL_TABLES


def test_ensure_embed_col_is_table_generic():
    from hydrahive.db._mirror_ddl import ensure_embed_col
    params = inspect.signature(ensure_embed_col).parameters
    assert "table" in params
    assert params["table"].default == "events"  # events-Verhalten unverändert


def test_vec_str_matches_mirror_embed_format():
    from hydrahive.db._mirror_cards import _vec_str
    assert _vec_str(None) is None
    assert _vec_str([]) is None
    assert _vec_str([1.0, 2.5, -3.0]) == "[1.0,2.5,-3.0]"


def test_loads_parses_jsonb_text():
    # asyncpg liefert JSONB als Text → get_card muss zurueck nach Objekt parsen
    from hydrahive.db._mirror_cards import _loads
    assert _loads('["a","b"]') == ["a", "b"]
    assert _loads('{"session_id":"s1"}') == {"session_id": "s1"}
    assert _loads(None) is None                 # None bleibt None
    assert _loads(["already"]) == ["already"]   # schon geparst → unveraendert
    assert _loads("not json") == "not json"     # kaputt → Rohwert


def test_recall_queries_callable():
    import inspect
    from hydrahive.db._mirror_cards import search_cards, top_cards_for
    assert inspect.iscoroutinefunction(top_cards_for)
    assert inspect.iscoroutinefunction(search_cards)
    assert "agent_id" in inspect.signature(top_cards_for).parameters
    assert "query" in inspect.signature(search_cards).parameters


def test_ensure_embed_col_rejects_unknown_table():
    import asyncio

    import pytest
    from hydrahive.db._mirror_ddl import ensure_embed_col
    with pytest.raises(ValueError):
        asyncio.run(ensure_embed_col(None, table="events; DROP TABLE x"))


def test_on_embed_model_change_ruft_ensure_embed_col_fuer_cards():
    """on_embed_model_change muss ensure_embed_col für BEIDE Tabellen aufrufen.

    Regression: nur 'events' wurde angepasst, 'cards' blieb bei alter dim → Suche kaputt.
    """
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, call, patch

    calls_made = []

    async def fake_ensure(conn, table="events"):
        calls_made.append(table)

    fake_conn = AsyncMock()
    fake_ctx = MagicMock()
    fake_ctx.__aenter__ = AsyncMock(return_value=fake_conn)
    fake_ctx.__aexit__ = AsyncMock(return_value=False)

    fake_pool = MagicMock()
    fake_pool.acquire = MagicMock(return_value=fake_ctx)

    with (
        patch("hydrahive.db.mirror._pool", fake_pool),
        patch("hydrahive.db.mirror.ensure_embed_col", side_effect=fake_ensure),
        patch("hydrahive.db.mirror._run_backfill", new_callable=AsyncMock),
    ):
        asyncio.run(
            __import__("hydrahive.db.mirror", fromlist=["on_embed_model_change"])
            .on_embed_model_change("baai/bge-m3-20251117")
        )

    assert "events" in calls_made, "ensure_embed_col für 'events' wurde nicht aufgerufen"
    assert "cards" in calls_made, "ensure_embed_col für 'cards' wurde nicht aufgerufen — Bug!"
