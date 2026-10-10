"""Datamining-Wortsuche über den Gesamtindex ``event_docs`` (docs/specs/datamining-gesamtindex.md, G2).

Vorher: ``ILIKE '%ganze Anfrage%'`` über ``events``, sortiert nach Datum – gemessen 0 % Treffer@5 bei echten
Fragen, bis 16 s Laufzeit. Jetzt: Anfrage in Wörter zerlegen, je Wort ``plainto_tsquery('simple', …)``, ODER
verknüpft (nie selbst gebauter tsquery-Text → keine Syntaxfehler/Injektion), Treffer per GIN, Rang
``ts_rank(…, 1)`` (gemessen 10.10. bester von 5 Varianten: echte Fragen 40 % / MRR 0,275, Median 18 ms).

Wichtig (gemessen 10.10.): Nur MIT Rang-Sortierung nimmt Postgres den GIN-Index (2–25 ms). Ohne ORDER BY wählte
der Planer den Sitzungs-Index und filterte alle 500k Zeilen (1,1 s).

Ausschnitt: je Treffer-Dokument EIN Ereignis (bei Werkzeug-Ergebnissen in Stücken das Stück mit dem Wort), Text
per ``ts_headline`` um die Fundstelle. Antwortformat wie bisher (Ereignis-Felder + ``snippet``) plus ``rank``.
"""
from __future__ import annotations

from hydrahive.db._mirror_scope import where as scope_where
from hydrahive.db._mirror_words import split_words

RANK = "ts_rank(d.tsv, q.q, 1)"
_BODY = "coalesce(e.text,'') || ' ' || coalesce(e.tool_output,'') || ' ' || coalesce(e.tool_input::text,'')"
_HEADLINE_OPTS = 'MaxFragments=2, MaxWords=30, MinWords=10, StartSel="", StopSel="", FragmentDelimiter=" … "'


def tsquery_sql(n_words: int) -> str:
    """``plainto_tsquery('simple', $1) || … || plainto_tsquery('simple', $n)`` – Wörter nur als Parameter."""
    return " || ".join(f"plainto_tsquery('simple', ${i})" for i in range(1, n_words + 1))


def build(q: str, *, event_type=None, agent_name=None, username=None, from_date=None, to_date=None,
          limit: int = 20, scope=None, dt=None) -> tuple[str, list] | None:
    """(SQL, Parameter) oder ``None`` bei leerer Anfrage (dann listet der Aufrufer nach Datum wie bisher).

    Ohne Wort ab 3 Zeichen (z. B. „KI“) wird die Anfrage als Ganzes gesucht – ebenfalls über den Index.
    Filter wirken auf die TREFFER-Dokumente (``event_docs``: Nutzer, Datum, Sicht) bzw. – für Typ und Agent, die
    ``event_docs`` nicht kennt – über das zugehörige Ereignis per EXISTS.
    """
    q = (q or "").strip()
    if not q:
        return None
    words = split_words(q) or [q[:200]]
    params: list = list(words)
    i = len(words) + 1
    where = ["d.tsv @@ q.q"]
    if username:
        where.append(f"d.username = ${i}"); params.append(username); i += 1
    if from_date:
        where.append(f"d.created_at >= ${i}"); params.append(dt(from_date)); i += 1
    if to_date:
        where.append(f"d.created_at <= ${i}"); params.append(dt(to_date)); i += 1
    if scope is not None:
        conds, extra, i = scope_where(scope, i, alias="d")
        where.extend(conds); params.extend(extra)
    ev_filter = []
    if event_type:
        # 'r:'-Dokumente bestehen nur aus tool_result (gemessen 10.10.: 20.000/20.000) → ohne Join entscheidbar.
        ev_filter.append(f"e.event_type = ${i}")
        where.append(f"(CASE WHEN d.doc_id LIKE 'r:%' THEN ${i} = 'tool_result' "
                     f"ELSE EXISTS (SELECT 1 FROM events e WHERE e.id = d.doc_id AND e.event_type = ${i}) END)")
        params.append(event_type); i += 1
    if agent_name:
        # Agentenname ist je Sitzung eindeutig (gemessen 10.10.: 0 Sitzungen mit zwei Namen) → Sitzungen EINMAL
        # bestimmen statt je Treffer-Dokument zu prüfen (vorher 0,6 s bei häufigen Wörtern, 24.016 Einzelabfragen).
        ev_filter.append(f"e.agent_name = ${i}")
        where.append(f"d.session_id = ANY(ARRAY(SELECT DISTINCT a.session_id FROM events a WHERE a.agent_name = ${i}"
                     + (f" AND a.username = ${i + 1}" if username else "") + "))")
        params.append(agent_name); i += 1
        if username:
            params.append(username); i += 1
    params.append(limit)
    sql = f"""
WITH q AS (SELECT {tsquery_sql(len(words))} AS q),
top AS (
  SELECT d.doc_id, d.session_id, d.created_at, {RANK} AS rank
  FROM event_docs d, q
  WHERE {' AND '.join(where)}
  ORDER BY rank DESC, d.created_at DESC
  LIMIT ${i})
SELECT ev.id, top.session_id, ev.username, ev.agent_name, ev.event_type, ev.created_at, ev.tool_name, ev.is_error,
       left(ts_headline('simple', ev.body, q.q, '{_HEADLINE_OPTS}'), 300) AS snippet,
       round(top.rank::numeric, 4)::float8 AS rank
FROM top, q
CROSS JOIN LATERAL (
  SELECT e.id, e.username, e.agent_name, e.event_type, e.created_at, e.tool_name, e.is_error, {_BODY} AS body
  FROM events e
  WHERE {_DOC_EVENTS.replace('d.doc_id', 'top.doc_id')}{' AND ' + ' AND '.join(ev_filter) if ev_filter else ''}
  ORDER BY (to_tsvector('simple', {_BODY}) @@ q.q) DESC,
           (e.id LIKE 'full:%'), e.message_id, e.block_index, e.chunk_index, e.id
  LIMIT 1) ev
ORDER BY top.rank DESC, top.created_at DESC"""
    return sql, params


# Ereignisse eines Dokuments (Schlüssel wie DOC_KEY in _mirror_docs: 'r:<tool_use_id>' oder Ereignis-id).
_DOC_EVENTS = ("((d.doc_id LIKE 'r:%' AND e.event_type = 'tool_result' AND e.tool_use_id = substr(d.doc_id, 3))"
               " OR (d.doc_id NOT LIKE 'r:%' AND e.id = d.doc_id))")
