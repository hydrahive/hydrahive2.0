from __future__ import annotations

import re

from hydrahive.tools._memory_store import load_filtered
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Sucht in den eigenen Memory-Notizen nach einer Phrase (case-insensitiv, "
    "über Schlüssel UND Inhalt). Liefert pro Treffer den Schlüssel und ein "
    "Snippet rund um den Match. Ergebnisse werden nach Relevanz × Confidence sortiert. "
    "Standardmäßig nur aktives Projekt + globale Einträge, ohne Abgelaufene/Veraltete."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Suchphrase oder Regex-Pattern.",
        },
        "regex": {
            "type": "boolean",
            "default": False,
            "description": "Query als Regex statt Substring.",
        },
        "max_results": {
            "type": "integer",
            "default": 20,
            "description": "Max. Treffer (1-100).",
        },
        "snippet_chars": {
            "type": "integer",
            "default": 120,
            "description": "Zeichen um den Match (20-500).",
        },
        "min_confidence": {
            "type": "number",
            "default": 0.0,
            "description": "Nur Einträge mit confidence >= diesem Wert (0.0–1.0).",
        },
        "project": {
            "type": "string",
            "description": (
                "Projekt-Filter. '*' für alle Projekte. "
                "Default: aktives Projekt aus Session-Kontext + globale Einträge."
            ),
        },
        "include_superseded": {
            "type": "boolean",
            "default": False,
            "description": "Auch veraltete/überschriebene Einträge einschließen.",
        },
    },
    "required": ["query"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    query = (args.get("query") or "").strip()
    if not query:
        return ToolResult.fail("Leere query")

    use_regex = bool(args.get("regex", False))
    max_results = max(1, min(int(args.get("max_results", 20)), 100))
    snippet_chars = max(20, min(int(args.get("snippet_chars", 120)), 500))
    min_confidence = max(0.0, min(float(args.get("min_confidence", 0.0)), 1.0))
    include_superseded = bool(args.get("include_superseded", False))
    filter_project = args.get("project") or None

    try:
        pattern = re.compile(query if use_regex else re.escape(query), re.IGNORECASE)
    except re.error as e:
        return ToolResult.fail(f"Ungültiger Regex: {e}")

    data = load_filtered(
        ctx.agent_id,
        filter_project=filter_project,
        active_project=ctx.project_id,
        include_superseded=include_superseded,
    )

    hits: list[dict] = []

    for key in sorted(data.keys()):
        entry = data[key]
        confidence = entry.get("confidence", 0.5)

        if confidence < min_confidence:
            continue

        content = entry.get("content", "")
        key_match = pattern.search(key)
        content_matches = list(pattern.finditer(content))

        if not key_match and not content_matches:
            continue

        if content_matches:
            first = content_matches[0]
            half = snippet_chars // 2
            start = max(0, first.start() - half)
            end = min(len(content), first.end() + half)
            snippet = content[start:end]
            if start > 0:
                snippet = "…" + snippet
            if end < len(content):
                snippet = snippet + "…"
        else:
            snippet = content[:snippet_chars] + ("…" if len(content) > snippet_chars else "")

        match_score = len(content_matches) + (2 if key_match else 0)

        hit: dict = {
            "key": key,
            "snippet": snippet,
            "confidence": confidence,
            "reinforcements": entry.get("reinforcements", 0),
            "is_latest": entry.get("is_latest", True),
            "matches_in_content": len(content_matches),
            "match_in_key": bool(key_match),
            "_sort_score": match_score * confidence,
        }
        if entry.get("project"):
            hit["project"] = entry["project"]
        if entry.get("expires_at"):
            hit["expires_at"] = entry["expires_at"]
        if not entry.get("is_latest", True) and entry.get("superseded_by"):
            hit["superseded_by"] = entry["superseded_by"]

        hits.append(hit)

    hits.sort(key=lambda h: h["_sort_score"], reverse=True)
    for h in hits:
        del h["_sort_score"]

    truncated = hits[:max_results]

    return ToolResult.ok({
        "query": query,
        "hits": truncated,
        "returned": len(truncated),
        "total_matches": len(hits),
        "total_keys": len(data),
    })


TOOL = Tool(name="search_memory", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="memory")
