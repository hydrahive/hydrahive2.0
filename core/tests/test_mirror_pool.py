"""Datamining-Pool plant jede Abfrage neu (force_custom_plan).

Gemessen 09.10.2026 (.2): asyncpg nutzt Prepared Statements. Nach 5 Ausführungen derselben Suche auf
einer Verbindung wählt Postgres einen generischen Plan ohne Trigramm-Index; die Suche nach „Hormon“
lief dann > 25 s (Timeout) statt 0,14 s. Das war die Ursache der sporadischen „Zeitüberschreitung“.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from hydrahive.db import _mirror_pool


def test_pool_erzwingt_individuelle_plaene():
    assert _mirror_pool.POOL_KW["server_settings"]["plan_cache_mode"] == "force_custom_plan"


def test_pool_wird_mit_diesen_einstellungen_erzeugt():
    fake = AsyncMock(return_value="POOL")
    with patch("asyncpg.create_pool", fake):
        assert asyncio.run(_mirror_pool.create_mirror_pool("postgresql://x")) == "POOL"
    kw = fake.call_args.kwargs
    assert fake.call_args.args == ("postgresql://x",)
    assert kw["server_settings"] == {"plan_cache_mode": "force_custom_plan"}
    assert kw["command_timeout"] == 10 and kw["max_size"] == 4


def test_mirror_init_nutzt_diesen_pool(monkeypatch):
    from hydrahive.db import mirror
    seen = {}

    async def fake_create(dsn):
        seen["dsn"] = dsn
        raise RuntimeError("stop nach Pool-Erzeugung")

    monkeypatch.setattr(mirror, "create_mirror_pool", fake_create)
    monkeypatch.setattr(mirror, "_HAS_ASYNCPG", True)
    monkeypatch.setenv("HH_PG_MIRROR_DSN", "postgresql://probe")
    asyncio.run(mirror.init())
    assert seen["dsn"] == "postgresql://probe"
