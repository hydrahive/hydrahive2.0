"""Gesamtindex: Suchdokumente je Werkzeug-Ergebnis bzw. Ereignis (docs/specs/datamining-gesamtindex.md, G1).

``event_docs`` hält NUR den Suchindex (``tsvector`` 'simple') + die Felder, die die Sicht (``_mirror_scope.where``)
braucht – kein Text-Duplikat. Ein Werkzeug-Ergebnis in mehreren 3.000er-Stücken wird EIN Dokument (alle Stücke
zusammen), sonst wären Wörter über Stückgrenzen unauffindbar (gemessen 09.10.: 49 % der Grenzen mitten im Wort).
Pflege ist best-effort: das Spiegeln selbst darf daran nie scheitern; Lücken holt der Nachhol-Lauf.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

MAX_DOC_CHARS = 1_000_000          # to_tsvector-Grenze (1 MB) mit Abstand

DDL = """
CREATE TABLE IF NOT EXISTS event_docs (
  doc_id      TEXT PRIMARY KEY,
  session_id  TEXT NOT NULL,
  username    TEXT,
  agent_id    TEXT,
  project_id  TEXT,
  created_at  TIMESTAMPTZ NOT NULL,
  tsv         TSVECTOR NOT NULL,
  built_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS event_docs_tsv     ON event_docs USING gin (tsv);
CREATE INDEX IF NOT EXISTS event_docs_user    ON event_docs (username, created_at);
CREATE INDEX IF NOT EXISTS event_docs_session ON event_docs (session_id);
CREATE INDEX IF NOT EXISTS events_tool_use_id ON events (tool_use_id) WHERE tool_use_id IS NOT NULL;
"""

# Ein Werkzeug-Ergebnis (event_type tool_result mit tool_use_id) = ein Dokument; alles andere je Ereignis.
DOC_KEY = ("CASE WHEN {a}.event_type = 'tool_result' AND {a}.tool_use_id IS NOT NULL "
           "THEN 'r:' || {a}.tool_use_id ELSE {a}.id END")
BODY = ("coalesce({a}.text,'') || ' ' || coalesce({a}.tool_output,'') || ' ' || coalesce({a}.tool_input::text,'') "
        "|| ' ' || coalesce({a}.tool_name,'')")

# Neu berechnen aus ALLEN Ereignissen der Dokumente; Stücke in Reihenfolge (Nachricht, Block, Stück; full: hinten).
REFRESH_SQL = f"""
INSERT INTO event_docs (doc_id, session_id, username, agent_id, project_id, created_at, tsv, built_at)
SELECT {DOC_KEY.format(a='e')} AS doc_id,
       min(e.session_id), min(e.username), min(e.agent_id), min(e.project_id), min(e.created_at),
       to_tsvector('simple', left(string_agg({BODY.format(a='e')}, ' '
           ORDER BY (e.id LIKE 'full:%'), e.message_id, e.block_index, e.chunk_index, e.id), {MAX_DOC_CHARS})),
       now()
FROM events e
WHERE (e.tool_use_id = ANY($1::text[]) AND e.event_type = 'tool_result')      -- Werkzeug-Ergebnisse (Index tool_use_id)
   OR (e.id = ANY($2::text[]) AND NOT (e.event_type = 'tool_result' AND e.tool_use_id IS NOT NULL))  -- Rest (PK)
GROUP BY 1
ON CONFLICT (doc_id) DO UPDATE SET
  session_id = EXCLUDED.session_id, username = EXCLUDED.username, agent_id = EXCLUDED.agent_id,
  project_id = EXCLUDED.project_id, created_at = EXCLUDED.created_at, tsv = EXCLUDED.tsv, built_at = now()
"""

# Dokumente, deren Ereignisse alle verschwunden sind (z. B. Rechunk ersetzt Stücke) → entfernen.
PRUNE_SQL = """
DELETE FROM event_docs d WHERE d.doc_id = ANY($1::text[])
  AND NOT EXISTS (SELECT 1 FROM events e WHERE e.event_type = 'tool_result' AND e.tool_use_id = substr(d.doc_id, 3)
                  AND d.doc_id LIKE 'r:%')
  AND NOT EXISTS (SELECT 1 FROM events e WHERE e.id = d.doc_id AND d.doc_id NOT LIKE 'r:%')
"""


def doc_key(event: dict) -> str:
    """Dokument-Schlüssel eines Ereignisses – identisch zu DOC_KEY im SQL."""
    if event.get("event_type") == "tool_result" and event.get("tool_use_id"):
        return f"r:{event['tool_use_id']}"
    return str(event["id"])


async def refresh_docs(conn, doc_ids) -> int:
    """Dokumente neu berechnen (Upsert) und verwaiste entfernen. Rückgabe: Anzahl angefragter Dokumente."""
    ids = sorted({d for d in doc_ids if d})
    if not ids:
        return 0
    tool_ids = [d[2:] for d in ids if d.startswith("r:")]
    event_ids = [d for d in ids if not d.startswith("r:")]
    await conn.execute(REFRESH_SQL, tool_ids, event_ids)
    await conn.execute(PRUNE_SQL, ids)
    return len(ids)


async def refresh_for_events(pool, events: list[dict]) -> None:
    """Nach dem Schreiben von Ereignissen: deren Dokumente aktualisieren. Best-effort – nie werfen."""
    if pool is None or not events:
        return
    try:
        async with pool.acquire() as conn:
            await refresh_docs(conn, [doc_key(e) for e in events])
    except Exception as e:  # noqa: BLE001 — Spiegeln darf am Index nie scheitern; Nachhol-Lauf schließt Lücken
        logger.warning("event_docs: Aktualisierung fehlgeschlagen (%d Ereignisse): %s", len(events), e)
