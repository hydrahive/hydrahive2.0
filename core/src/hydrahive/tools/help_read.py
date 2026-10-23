"""Hilfe-Assistent: einen Handbuch-Artikel lesen (docs/plans/help-assistant.md)."""
from __future__ import annotations

from hydrahive.helpdesk import _lang
from hydrahive.helpdesk import _manual as manual
from hydrahive.tools.base import Tool, ToolContext, ToolResult

MAX_CHARS = 12000
_DESCRIPTION = (
    "Liest einen Artikel aus dem HydraHive-Handbuch in der Sprache des Nutzers. topic ist der Name aus help_search "
    "(z. B. „agents“, „llm“, „containers“) oder „guide“ für das komplette Benutzerhandbuch."
)
_SCHEMA = {
    "type": "object",
    "properties": {"topic": {"type": "string", "description": "Thema, z. B. „agents“ oder „guide“"}},
    "required": ["topic"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    topic = str(args.get("topic") or "").strip()
    lang = _lang.help_lang(ctx.user_id)
    text = manual.read(topic, lang)
    if text is None:
        return ToolResult.fail(f"Unbekanntes Thema. Vorhanden: {', '.join(manual.topics(lang))}")
    truncated = len(text) > MAX_CHARS
    return ToolResult.ok({"topic": topic, "text": text[:MAX_CHARS], "truncated": truncated})


TOOL = Tool(name="help_read", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="help")
