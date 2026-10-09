"""Volle Werkzeug-Ausgaben in den Datamining-Index nachtragen (docs/specs/datamining-volltext-werkzeuge.md).

Der Runner kürzt Werkzeug-Ausgaben auf ``tool_result_max_chars`` des Agenten, bevor sie gespeichert und
gespiegelt werden. Der volle Text steht nur in ``sessions.db → tool_calls.result``. Hier wird der Rest – der Teil
nach der Grenze – als zusätzliche ``tool_result``-Stücke in ``events`` geschrieben: nur für die Volltextsuche,
ohne Embedding, Secrets geschwärzt, höchstens ``MAX_CHARS`` je Aufruf (darüber Anfang + Ende).
"""
from __future__ import annotations

from hydrahive.credentials.redaction import redact_detected
from hydrahive.db._mirror_explode import CHUNK_CHARS

MAX_CHARS = 200_000          # Tills Freigabe 09.10.: darüber nur Anfang + Ende (Logs/Binärkram)
SKIP_EMBED = "skip:full"     # embedding_model-Markierung: Fortsetzungs-Stücke bekommen kein Embedding
GAP = "\n\n[… {n} Zeichen ausgelassen …]\n\n"


def rest_text(full: str, limit: int) -> str:
    """Teil des vollen Textes, der dem Agenten (und damit dem Index) gefehlt hat – auf MAX_CHARS begrenzt.

    ``limit`` = Grenze, bei der der Runner abgeschnitten hat. Das Gesamtstück (sichtbarer Teil + Rest) bleibt
    unter MAX_CHARS; ist der Text länger, bleibt vom Rest der Anfang und das Ende übrig."""
    if not full or limit <= 0 or len(full) <= limit:
        return ""
    rest = full[limit:]
    budget = max(0, MAX_CHARS - limit)
    if len(rest) <= budget:
        return rest
    if budget < 2:
        return ""
    head, tail = budget // 2, budget - budget // 2
    return rest[:head] + GAP.format(n=len(rest) - budget) + rest[-tail:]


def agent_text(stored: str) -> str:
    """Text, den der Agent gesehen hat. ``tool_calls.result`` ist das JSON von ``ToolResult`` – der Runner schneidet
    ``ToolResult.to_llm()`` ab (runner/dispatcher.to_tool_result_block), also muss hier dieselbe Fassung entstehen.
    Gemessen 09.10.: Anfang im Index == to_llm() bei 200/200 Stichproben, == Rohtext nur 3/200."""
    import json

    from hydrahive.tools.base import ToolResult
    try:
        d = json.loads(stored)
    except (TypeError, ValueError):
        return stored or ""
    if not isinstance(d, dict) or "success" not in d:
        return stored
    return ToolResult(success=bool(d.get("success")), output=d.get("output"), error=d.get("error"),
                      metadata=d.get("metadata") or {}).to_llm()


def chunks(text: str, size: int = CHUNK_CHARS) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)] if text else []


def event_id(tool_call_id: str, n: int) -> str:
    """Eigene, stabile ID je Stück → zweiter Lauf schreibt nichts doppelt (ON CONFLICT DO NOTHING)."""
    return f"full:{tool_call_id}:{n}"


def build_events(call: dict, base: dict) -> list[dict]:
    """Ereignisse für einen gekürzten Werkzeugaufruf. ``call``: id, tool_name, tool_use_id, result,
    truncate_limit_chars, status. ``base``: Felder des Original-Ergebnis-Ereignisses (Sitzung, Nutzer, Projekt …)."""
    rest = rest_text(agent_text(call.get("result") or ""), int(call.get("truncate_limit_chars") or 0))
    if not rest:
        return []
    parts = chunks(redact_detected(rest))
    return [{
        **base,
        "id": event_id(call["id"], i),
        "chunk_index": i, "chunk_total": len(parts),
        "event_type": "tool_result",
        "tool_name": call.get("tool_name"),
        "tool_use_id": call.get("tool_use_id"),
        "tool_output": part,
        "is_error": call.get("status") == "error",
    } for i, part in enumerate(parts)]
