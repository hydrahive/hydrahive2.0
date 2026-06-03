from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Sendet eine E-Mail. Nutzt standardmäßig die globalen Mail-Settings "
    "(System → Einstellungen → Mail). Eine agent-eigene `smtp`-Tool-Config "
    "(host, port, user, password, from, use_tls) überschreibt diese optional."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "to": {"type": "string", "description": "Empfänger (komma-separiert für mehrere)."},
        "subject": {"type": "string", "description": "Betreff."},
        "body": {"type": "string", "description": "Klartext-Body."},
        "cc": {"type": "string", "description": "CC-Empfänger (optional)."},
    },
    "required": ["to", "subject", "body"],
}


def _settings_smtp() -> dict:
    """SMTP-Config aus den globalen Mail-Settings — dieselbe Quelle wie der Watcher."""
    from hydrahive.settings import settings
    return {
        "host": settings.mail_smtp_host,
        "port": settings.mail_smtp_port,
        "user": settings.mail_smtp_user,
        "password": settings.mail_smtp_password,
        "from": settings.mail_from,
        "use_tls": settings.mail_smtp_use_tls,
    }


def _resolve_smtp_cfg(tool_config: dict) -> dict:
    """Per-Agent-`smtp`-Override gewinnt, sonst globale Settings (Single Source).

    Ein Override zählt nur als gültig, wenn er host UND from trägt — eine halb
    gefüllte Tool-Config fällt sauber auf die globalen Settings zurück.
    """
    override = tool_config.get("smtp") or {}
    if override.get("host") and override.get("from"):
        return override
    return _settings_smtp()


def _send_sync(cfg: dict, msg: EmailMessage) -> None:
    host = cfg.get("host", "")
    port = int(cfg.get("port", 587))
    use_tls = bool(cfg.get("use_tls", True))
    user = cfg.get("user")
    pw = cfg.get("password")

    with smtplib.SMTP(host, port, timeout=30) as s:
        s.ehlo()
        if use_tls:
            s.starttls()
            s.ehlo()
        if user and pw:
            s.login(user, pw)
        s.send_message(msg)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    cfg = _resolve_smtp_cfg(ctx.config)
    if not cfg.get("host") or not cfg.get("from"):
        return ToolResult.fail(
            "SMTP nicht konfiguriert (Mail-Settings unter System → Einstellungen → Mail "
            "ausfüllen, oder agent-eigene smtp-Tool-Config setzen) — send_mail ist aktuell ein Stub."
        )

    to = (args.get("to") or "").strip()
    subject = (args.get("subject") or "").strip()
    body = args.get("body") or ""
    cc = (args.get("cc") or "").strip()
    if not to or not subject:
        return ToolResult.fail("to und subject sind Pflicht")

    msg = EmailMessage()
    msg["From"] = cfg["from"]
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        await asyncio.to_thread(_send_sync, cfg, msg)
    except Exception as e:
        return ToolResult.fail(f"Mail-Versand fehlgeschlagen: {e}")

    return ToolResult.ok(f"Mail an {to} gesendet", to=to, subject=subject)


TOOL = Tool(name="send_mail", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="mail")
