"""Discord schreiben: discord_post, discord_reply, discord_edit.

Dünne Hülle — Logik in communication/discord/ops_write.py (lazy import).
"""
from __future__ import annotations

from typing import Awaitable, Callable

from hydrahive.tools.base import Tool, ToolContext, ToolResult

_TEXT = {"type": "string", "description": (
    "Nachrichtentext (Discord-Markdown). Über 2000 Zeichen wird an Absätzen auf bis zu "
    "4 Nachrichten verteilt. @everyone/@here/Rollen pingen nicht.")}

_POST_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": (
            "ID eines freigegebenen Textkanals oder Forums. Bei einem Forum wird ein neuer "
            "Beitrag angelegt.")},
        "text": _TEXT,
        "title": {"type": "string", "description": "Nur Forum: Titel des neuen Beitrags (Pflicht, max. 100 Zeichen)."},
        "tags": {"type": "array", "items": {"type": "string"}, "description": (
            "Nur Forum: Tag-Namen (max. 5, siehe discord_channels). Groß/klein und Emoji egal.")},
    },
    "required": ["channel_id", "text"],
}

_REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": (
            "ID des Forum-Beitrags (oder eines freigegebenen Textkanals), in dem geantwortet wird.")},
        "text": _TEXT,
        "reply_to": {"type": "string", "description": (
            "Optional: Nachrichten-ID, auf die sich die Antwort bezieht (Discord-Antwort-Verweis).")},
    },
    "required": ["channel_id", "text"],
}

_EDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "channel_id": {"type": "string", "description": "Kanal- bzw. Beitrag-ID, in der die Nachricht steht."},
        "message_id": {"type": "string", "description": (
            "ID der eigenen Bot-Nachricht. Eröffnung eines Forum-Beitrags: Beitrag-ID.")},
        "text": {"type": "string", "description": "Neuer vollständiger Text (max. 2000 Zeichen)."},
    },
    "required": ["channel_id", "message_id", "text"],
}

_Op = Callable[..., Awaitable[str]]


async def _run(ctx: ToolContext, op_name: str, **kwargs) -> ToolResult:
    from hydrahive.communication.discord import ops_access, ops_write
    op: _Op = getattr(ops_write, op_name)
    try:
        scope = ops_access.open_scope(ctx.user_id)
        return ToolResult.ok(await op(scope, ctx.agent_id, **kwargs))
    except ops_access.DiscordToolError as e:
        return ToolResult.fail(str(e))


async def _post(args: dict, ctx: ToolContext) -> ToolResult:
    tags = args.get("tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    return await _run(ctx, "post", channel_id=args.get("channel_id"),
                      text=args.get("text") or "", title=args.get("title"), tags=tags)


async def _reply(args: dict, ctx: ToolContext) -> ToolResult:
    return await _run(ctx, "reply", channel_id=args.get("channel_id"),
                      text=args.get("text") or "", reply_to=args.get("reply_to"))


async def _edit(args: dict, ctx: ToolContext) -> ToolResult:
    return await _run(ctx, "edit", channel_id=args.get("channel_id"),
                      message_id=args.get("message_id"), text=args.get("text") or "")


TOOL_POST = Tool(
    name="discord_post",
    description=(
        "Postet in einen freigegebenen Discord-Kanal. Textkanal → Nachricht. Forum → neuer "
        "Beitrag mit title (Pflicht), text und optional tags. Zum Antworten in einem "
        "bestehenden Beitrag discord_reply nutzen."),
    schema=_POST_SCHEMA, execute=_post, category="discord",
)

TOOL_REPLY = Tool(
    name="discord_reply",
    description=(
        "Antwortet in einem Forum-Beitrag (Beitrag-ID als channel_id) oder Textkanal, optional "
        "als Antwort auf eine bestimmte Nachricht (reply_to)."),
    schema=_REPLY_SCHEMA, execute=_reply, category="discord",
)

TOOL_EDIT = Tool(
    name="discord_edit",
    description="Bearbeitet eine eigene, vom Bot gesendete Discord-Nachricht. Fremde Nachrichten sind tabu.",
    schema=_EDIT_SCHEMA, execute=_edit, category="discord",
)
