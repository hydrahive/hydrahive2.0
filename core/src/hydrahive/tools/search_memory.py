from __future__ import annotations

import re

from hydrahive.tools._memory_store import load
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Sucht in den eigenen Memory-Notizen nach einer Phrase (case-insensitiv, "
    "über Schlüssel UND Inhalt). Liefert pro Treffer den Schlüssel und ein "
    "Snippet rund um den Match. Mit `regex=true` wird die Query als regulärer "
    "Ausdruck interpretiert."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Suchphrase oder Regex-Pattern."},
        "regex": {"type": "boolean", "default": False, "description": "Query als Regex statt Substring."},
        "max_results": {"type": "integer", "default": 20, "description": "Max. Treffer (1-100)."},
        "snippet_chars": {"type": "integer", "default": 120, "description": "Zeichen um den Match (20-500)."},
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

    try:
        pattern = re.compile(query if use_regex else re.escape(query), re.IGNORECASE)
    except re.error as e:
        return ToolResult.fail(f"Ungültiger Regex: {e}")

    data = load(ctx.agent_id)
    hits: list[dict] = []

    for key in sorted(data.keys()):
        content = data[key]
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

        hits.append({
            "key": key,
            "snippet": snippet,
            "matches_in_content": len(content_matches),
            "match_in_key": bool(key_match),
        })
        if len(hits) >= max_results:
            break

    return ToolResult.ok({"query": query, "hits": hits, "count": len(hits), "total_keys": len(data)})


TOOL = Tool(name="search_memory", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute)
