#!/usr/bin/env python3
"""HydraHive Datamining MCP-Server.

Sucht in der PostgreSQL-Events-Tabelle — kein Core-Code, kein Prompt.
DSN via Env-Var PG_MIRROR_DSN oder HH_PG_MIRROR_DSN.
Semantic Search: HH_EMBED_MODEL + Provider-API-Key (z.B. NVIDIA_NIM_API_KEY).
"""
import json
import os
from typing import Optional

import psycopg2
import psycopg2.extras
from mcp.server.fastmcp import FastMCP

DSN = os.environ.get("PG_MIRROR_DSN") or os.environ.get("HH_PG_MIRROR_DSN", "")
EMBED_MODEL = os.environ.get("HH_EMBED_MODEL", "")

mcp = FastMCP("datamining")
_conn: "psycopg2.extensions.connection | None" = None


def _get_conn() -> "psycopg2.extensions.connection":
    global _conn
    if not DSN:
        raise RuntimeError("PG_MIRROR_DSN nicht gesetzt")
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(DSN, cursor_factory=psycopg2.extras.RealDictCursor)
        _conn.autocommit = True
    return _conn


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    cur = _get_conn().cursor()
    cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def _snippet(text: str | None, query: str, max_len: int = 300) -> str | None:
    if not text:
        return None
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[:max_len] + ("…" if len(text) > max_len else "")
    start = max(0, idx - 80)
    end = min(len(text), idx + 220)
    snip = text[start:end]
    if start > 0:
        snip = "…" + snip
    if end < len(text):
        snip = snip + "…"
    return snip


@mcp.tool()
def search(
    query: str,
    event_type: Optional[str] = None,
    username: Optional[str] = None,
    agent_name: Optional[str] = None,
    tool_name: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Durchsucht alle Chat-Events nach einem Begriff.

    Durchsucht: Textnachrichten, Tool-Outputs, Tool-Inputs.
    Optionale Filter: event_type, username, agent_name, tool_name, Datumsbereich.
    event_type: user_input | assistant_text | tool_call | tool_result | compaction | thinking
    """
    pat = f"%{query}%"
    where = ["(text ILIKE %s OR tool_output ILIKE %s OR tool_input::text ILIKE %s OR tool_name ILIKE %s)"]
    params: list = [pat, pat, pat, pat]

    if event_type:
        where.append("event_type = %s"); params.append(event_type)
    if username:
        where.append("username = %s"); params.append(username)
    if agent_name:
        where.append("agent_name = %s"); params.append(agent_name)
    if tool_name:
        where.append("tool_name = %s"); params.append(tool_name)
    if from_date:
        where.append("created_at >= %s"); params.append(from_date)
    if to_date:
        where.append("created_at <= %s"); params.append(to_date)

    params.append(limit)
    sql = f"""
        SELECT id, session_id, message_id, username, agent_name, project_id,
               event_type, created_at, tool_name, is_error,
               text, tool_output, tool_input,
               chunk_index, chunk_total
        FROM events
        WHERE {' AND '.join(where)}
        ORDER BY created_at DESC
        LIMIT %s
    """
    rows = _rows(sql, tuple(params))

    results = []
    for r in rows:
        hit: dict = {
            "id": r["id"],
            "session_id": r["session_id"],
            "event_type": r["event_type"],
            "created_at": str(r["created_at"]),
            "username": r["username"],
            "agent_name": r["agent_name"],
        }
        if r["tool_name"]:
            hit["tool_name"] = r["tool_name"]
        if r["is_error"]:
            hit["is_error"] = True
        if r["chunk_total"] and r["chunk_total"] > 1:
            hit["chunk"] = f"{r['chunk_index']+1}/{r['chunk_total']}"

        # Snippet aus dem relevanten Feld
        hit["snippet"] = (
            _snippet(r["text"], query)
            or _snippet(r["tool_output"], query)
            or _snippet(json.dumps(r["tool_input"]) if r["tool_input"] else None, query)
        )
        results.append(hit)

    return json.dumps({"count": len(results), "results": results}, ensure_ascii=False, indent=2)


@mcp.tool()
def get_session(session_id: str) -> str:
    """Gibt alle Events einer Session chronologisch zurück.

    Chunks werden automatisch zusammengesetzt.
    Liefert ein vollständiges Bild der Session inkl. aller Tool-Calls und Outputs.
    """
    rows = _rows("""
        SELECT message_id, block_index, chunk_index, chunk_total,
               event_type, created_at, username, agent_name,
               tool_name, tool_use_id, tool_input, is_error,
               text, tool_output
        FROM events
        WHERE session_id = %s
        ORDER BY created_at, block_index, chunk_index
    """, (session_id,))

    if not rows:
        return json.dumps({"error": f"Session {session_id!r} nicht gefunden"})

    # Chunks zusammensetzen: gleiche message_id + block_index → ein Event
    merged: list[dict] = []
    buf: dict | None = None

    for r in rows:
        key = (r["message_id"], r["block_index"])
        if buf is None or (buf["_key"]) != key:
            if buf:
                merged.append(_finalize(buf))
            buf = {
                "_key": key,
                "event_type": r["event_type"],
                "created_at": str(r["created_at"]),
                "username": r["username"],
                "agent_name": r["agent_name"],
                "tool_name": r["tool_name"],
                "tool_use_id": r["tool_use_id"],
                "tool_input": r["tool_input"],
                "is_error": r["is_error"],
                "_text_parts": [r["text"]] if r["text"] else [],
                "_output_parts": [r["tool_output"]] if r["tool_output"] else [],
            }
        else:
            if r["tool_output"]:
                buf["_output_parts"].append(r["tool_output"])
            if r["text"]:
                buf["_text_parts"].append(r["text"])

    if buf:
        merged.append(_finalize(buf))

    meta = _rows("""
        SELECT id, username, agent_name, project_id, title, status, started_at, updated_at
        FROM sessions WHERE id = %s
    """, (session_id,))

    return json.dumps({
        "session": dict(meta[0]) if meta else {"id": session_id},
        "event_count": len(merged),
        "events": merged,
    }, ensure_ascii=False, indent=2, default=str)


def _finalize(buf: dict) -> dict:
    out = {k: v for k, v in buf.items() if not k.startswith("_")}
    text = "\n".join(p for p in buf["_text_parts"] if p)
    output = "\n".join(p for p in buf["_output_parts"] if p)
    if text:
        out["text"] = text
    if output:
        out["tool_output"] = output
    return out


@mcp.tool()
def list_sessions(
    username: Optional[str] = None,
    agent_name: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Listet die letzten Sessions auf mit Event-Anzahl und Zeitstempeln.

    Optionale Filter: username, agent_name.
    """
    where = ["1=1"]
    params: list = []
    if username:
        where.append("s.username = %s"); params.append(username)
    if agent_name:
        where.append("s.agent_name = %s"); params.append(agent_name)
    params.append(limit)

    rows = _rows(f"""
        SELECT s.id, s.username, s.agent_name, s.project_id, s.title, s.status,
               s.started_at, s.updated_at,
               COUNT(e.id) AS event_count
        FROM sessions s
        LEFT JOIN events e ON e.session_id = s.id
        WHERE {' AND '.join(where)}
        GROUP BY s.id
        ORDER BY s.updated_at DESC NULLS LAST
        LIMIT %s
    """, tuple(params))

    return json.dumps({
        "count": len(rows),
        "sessions": [dict(r) for r in rows],
    }, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
def semantic_search(
    query: str,
    event_type: Optional[str] = None,
    username: Optional[str] = None,
    agent_name: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Semantische Ähnlichkeitssuche über alle Chat-Events via pgvector.

    Findet Events die inhaltlich ähnlich zur Query sind — auch ohne exakte Wortübereinstimmung.
    Erfordert konfiguriertes Embedding-Modell (HH_EMBED_MODEL) und befüllte Embeddings.
    Gibt Ergebnisse sortiert nach Ähnlichkeit zurück (höchste zuerst).
    event_type: user_input | assistant_text | tool_call | tool_result | compaction | thinking
    """
    if not EMBED_MODEL:
        return json.dumps({"error": "HH_EMBED_MODEL nicht gesetzt"})

    try:
        import litellm
        resp = litellm.embedding(model=EMBED_MODEL, input=[query])
        vec: list[float] = resp.data[0]["embedding"]
    except Exception as e:
        return json.dumps({"error": f"Embedding fehlgeschlagen: {e}"})

    vec_str = "[" + ",".join(str(x) for x in vec) + "]"

    where = ["embedding IS NOT NULL"]
    filter_params: list = []

    if event_type:
        where.append("event_type = %s"); filter_params.append(event_type)
    if username:
        where.append("username = %s"); filter_params.append(username)
    if agent_name:
        where.append("agent_name = %s"); filter_params.append(agent_name)
    if from_date:
        where.append("created_at >= %s"); filter_params.append(from_date)
    if to_date:
        where.append("created_at <= %s"); filter_params.append(to_date)

    sql = f"""
        SELECT id, session_id, username, agent_name, event_type, created_at,
               tool_name, is_error,
               left(coalesce(text, tool_output, ''), 300) AS snippet,
               round((1 - (embedding <=> %s::vector))::numeric, 3) AS similarity
        FROM events
        WHERE {' AND '.join(where)}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    # vec_str zweimal: für similarity-Berechnung und ORDER BY
    all_params = tuple([vec_str] + filter_params + [vec_str, limit])

    rows = _rows(sql, all_params)

    results = []
    for r in rows:
        hit: dict = {
            "id": r["id"],
            "session_id": r["session_id"],
            "event_type": r["event_type"],
            "created_at": str(r["created_at"]),
            "username": r["username"],
            "agent_name": r["agent_name"],
            "similarity": float(r["similarity"]) if r["similarity"] else None,
            "snippet": r["snippet"],
        }
        if r["tool_name"]:
            hit["tool_name"] = r["tool_name"]
        if r["is_error"]:
            hit["is_error"] = True
        results.append(hit)

    return json.dumps({"count": len(results), "results": results}, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
