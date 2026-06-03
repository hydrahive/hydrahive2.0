from __future__ import annotations

import asyncio

from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Liest E-Mails aus dem Postfach (read-only). Nutzt standardmäßig die globalen "
    "Mail-Settings (System → Einstellungen → Mail); eine agent-eigene `imap`-Tool-"
    "Config (host, port, user, password) überschreibt diese optional. Verändert "
    "nichts am Server — markiert nichts als gelesen."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "unread_only": {"type": "boolean",
                        "description": "Nur ungelesene Mails (UNSEEN). Default: true."},
        "limit": {"type": "integer",
                  "description": "Maximale Anzahl Mails (1–50). Default: 10."},
        "folder": {"type": "string", "description": "IMAP-Ordner. Default: INBOX."},
    },
}

_MAX_LIMIT = 50
_DEFAULT_LIMIT = 10
_TOOL_BODY_BUDGET = 1500


def _settings_imap() -> dict:
    """IMAP-Config aus den globalen Mail-Settings — dieselbe Quelle wie der Watcher."""
    from hydrahive.settings import settings
    return {
        "imap_host": settings.mail_imap_host,
        "imap_port": settings.mail_imap_port,
        "imap_user": settings.mail_imap_user,
        "imap_password": settings.mail_imap_password,
    }


def _resolve_imap_cfg(tool_config: dict) -> dict:
    """Per-Agent-`imap`-Override gewinnt, sonst globale Settings (Single Source)."""
    o = tool_config.get("imap") or {}
    if o.get("host") and o.get("user"):
        return {
            "imap_host": o["host"],
            "imap_port": o.get("port", 993),
            "imap_user": o["user"],
            "imap_password": o.get("password", ""),
        }
    return _settings_imap()


def _format(mails: list) -> str:
    blocks = []
    for i, m in enumerate(mails, 1):
        snippet = (m.body or "").strip()[:_TOOL_BODY_BUDGET]
        blocks.append(
            f"[{i}] Von: {m.from_name} <{m.from_addr}> | {m.date}\n"
            f"Betreff: {m.subject}\n{snippet}"
        )
    return "\n\n---\n\n".join(blocks)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    cfg = _resolve_imap_cfg(ctx.config)
    if not cfg.get("imap_host") or not cfg.get("imap_user"):
        return ToolResult.fail(
            "IMAP nicht konfiguriert — Mail-Settings unter System → Einstellungen → Mail "
            "ausfüllen (IMAP-Host leer = wie SMTP), oder agent-eigene imap-Tool-Config setzen."
        )

    limit = args.get("limit") or _DEFAULT_LIMIT
    limit = max(1, min(int(limit), _MAX_LIMIT))
    folder = (args.get("folder") or "INBOX").strip() or "INBOX"
    unread_only = args.get("unread_only", True)
    criterion = "UNSEEN" if unread_only else "ALL"

    from hydrahive.communication.mail import imap_poll
    mails = await asyncio.to_thread(
        imap_poll.fetch, cfg, folder, criterion=criterion, limit=limit)
    mails = list(reversed(mails))  # neueste zuerst

    if not mails:
        scope = "ungelesene " if unread_only else ""
        return ToolResult.ok(f"Keine {scope}Nachrichten in {folder}.", count=0)

    return ToolResult.ok(_format(mails), count=len(mails))


TOOL = Tool(name="read_mail", description=_DESCRIPTION, schema=_SCHEMA,
            execute=_execute, category="mail")
