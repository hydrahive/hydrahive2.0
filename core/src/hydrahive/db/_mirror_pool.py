"""Mirror — Verbindungs-Pool zur Datamining-Datenbank.

``plan_cache_mode = force_custom_plan``: Datamining-Suchen sind Muster (``ILIKE '%…%'``). asyncpg nutzt
Prepared Statements; ab der 6. Ausführung auf derselben Verbindung wählt Postgres sonst einen *generischen*
Plan. Der kennt das Suchwort nicht, nimmt den Nutzer-Index statt der Trigramm-Indexe und geht für seltene
Wörter die ganze Tabelle des Nutzers durch – bis zur Zeitüberschreitung.
Gemessen 09.10.2026 auf .2: „Hormon“ nach 6 Suchen > 25 s, mit dieser Einstellung 0,14 s. Planen kostet
je Abfrage nur Millisekunden.
"""
from __future__ import annotations

POOL_KW: dict = {
    "min_size": 1,
    "max_size": 4,
    "command_timeout": 10,
    "server_settings": {"plan_cache_mode": "force_custom_plan"},
}


async def create_mirror_pool(dsn: str):
    import asyncpg  # optional: mirror.py prüft vorher _HAS_ASYNCPG
    return await asyncpg.create_pool(dsn, **POOL_KW)
