"""Gesamtindex nachholen + Abdeckung zählen (docs/specs/datamining-gesamtindex.md, G1).

Sicherheitsnetz zur Pflege beim Spiegeln: findet Dokumente, die FEHLEN oder VERALTET sind (ein Ereignis wurde nach
dem letzten Bau gespiegelt: ``events.mirrored_at > event_docs.built_at``) und baut sie neu. Ist der Index leer,
wird er in einem Rutsch aufgebaut (gemessen 09.10.: ~80 s für 573k Ereignisse). Idempotent: zweiter Lauf = 0.

Voll-Aufbau auch bei NICHT leerem Index, sobald mindestens ``FULL_BUILD_MIN_MISSING`` Dokumente fehlen: Nach dem
ersten Start mit G1 füllt die Pflege beim Spiegeln die Tabelle sofort mit neuen Nachrichten, bevor das Nachholen
läuft (Befund 10.10.: 2.128 Dokumente da, 499.690 fehlend → nur Runden à 2.000 statt eines Rutsches).
"""
from __future__ import annotations

import logging

from hydrahive.db._mirror_docs import BODY, DDL, DOC_KEY, MAX_DOC_CHARS, refresh_docs

logger = logging.getLogger(__name__)

BATCH = 2000
FULL_BUILD_MIN_MISSING = 20000   # ab so vielen fehlenden Dokumenten lohnt der Rutsch (Zählen bis hier: ~1,5 s)
BUILD_TIMEOUT = 1800        # Sekunden; der Pool hat sonst command_timeout 10 s

_FULL_BUILD = f"""
INSERT INTO event_docs (doc_id, session_id, username, agent_id, project_id, created_at, tsv, built_at)
SELECT {DOC_KEY.format(a='e')}, min(e.session_id), min(e.username), min(e.agent_id), min(e.project_id),
       min(e.created_at),
       to_tsvector('simple', left(string_agg({BODY.format(a='e')}, ' '
           ORDER BY (e.id LIKE 'full:%'), e.message_id, e.block_index, e.chunk_index, e.id), {MAX_DOC_CHARS})),
       now()
FROM events e GROUP BY 1
ON CONFLICT (doc_id) DO NOTHING
"""

# Fehlende Dokumente zählen, aber höchstens bis $1 (für die Entscheidung Voll-Aufbau ja/nein reicht das).
_MISSING_UP_TO = f"""
SELECT count(*) FROM (
  SELECT DISTINCT {DOC_KEY.format(a='e')}
  FROM events e LEFT JOIN event_docs d ON d.doc_id = {DOC_KEY.format(a='e')}
  WHERE d.doc_id IS NULL
  LIMIT $1) m
"""

# Fehlend ODER veraltet. LEFT JOIN über den Schlüssel-Ausdruck; DISTINCT, weil Stücke denselben Schlüssel teilen.
_PENDING = f"""
SELECT DISTINCT {DOC_KEY.format(a='e')} AS k
FROM events e LEFT JOIN event_docs d ON d.doc_id = {DOC_KEY.format(a='e')}
WHERE d.doc_id IS NULL OR e.mirrored_at > d.built_at
LIMIT $1
"""

_COVERAGE = f"""
SELECT count(DISTINCT {DOC_KEY.format(a='e')}) FILTER (WHERE d.doc_id IS NULL) AS missing,
       count(DISTINCT {DOC_KEY.format(a='e')}) FILTER (WHERE d.doc_id IS NOT NULL AND e.mirrored_at > d.built_at) AS stale,
       (SELECT count(*) FROM event_docs) AS docs
FROM events e LEFT JOIN event_docs d ON d.doc_id = {DOC_KEY.format(a='e')}
"""


async def ensure(conn) -> None:
    """Tabelle + Indizes anlegen (additiv, IF NOT EXISTS). Fehler nicht schlucken – der Aufrufer loggt."""
    await conn.execute(DDL, timeout=BUILD_TIMEOUT)


async def sync_docs(pool, *, max_rounds: int = 1000) -> dict:
    """Index vervollständigen. Rückgabe: {'full_build': bool, 'refreshed': n, 'rounds': n}."""
    stats = {"full_build": False, "refreshed": 0, "rounds": 0}
    if pool is None:
        return stats
    async with pool.acquire() as conn:
        missing = await conn.fetchval(_MISSING_UP_TO, FULL_BUILD_MIN_MISSING, timeout=BUILD_TIMEOUT)
        if missing >= FULL_BUILD_MIN_MISSING:
            await conn.execute(_FULL_BUILD, timeout=BUILD_TIMEOUT)
            stats["full_build"] = True
        for _ in range(max_rounds):
            keys = [r["k"] for r in await conn.fetch(_PENDING, BATCH, timeout=BUILD_TIMEOUT)]
            if not keys:
                break
            stats["refreshed"] += await refresh_docs(conn, keys)
            stats["rounds"] += 1
            if len(keys) < BATCH:
                break
    logger.info("event_docs nachgeholt: %s", stats)
    return stats


async def coverage(pool) -> dict:
    """Wie vollständig ist der Index? missing/stale = Dokumente, die (noch) nicht oder veraltet im Index sind."""
    if pool is None:
        return {"active": False}
    async with pool.acquire() as conn:
        r = await conn.fetchrow(_COVERAGE, timeout=BUILD_TIMEOUT)
    return {"active": True, "docs": r["docs"], "missing": r["missing"], "stale": r["stale"]}
