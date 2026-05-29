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
