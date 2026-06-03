from __future__ import annotations

import asyncio
from email.message import EmailMessage
from email.utils import parseaddr

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


def _is_qualified_address(from_value: str) -> bool:
    """True wenn der From-Wert eine vollständige Mailadresse enthält (auch als
    'Name <adresse@domain>'). Sonst lehnt der Mailserver mit einem kryptischen
    504 'need fully-qualified address' ab."""
    addr = parseaddr(from_value or "")[1]
    parts = addr.split("@")
    return len(parts) == 2 and all(p.strip() for p in parts)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    cfg = _resolve_smtp_cfg(ctx.config)
    if not cfg.get("host") or not cfg.get("from"):
        return ToolResult.fail(
            "SMTP nicht konfiguriert (Mail-Settings unter System → Einstellungen → Mail "
            "ausfüllen, oder agent-eigene smtp-Tool-Config setzen) — send_mail ist aktuell ein Stub."
        )

    if not _is_qualified_address(cfg["from"]):
        return ToolResult.fail(
            f"Absender (From) ist keine vollständige Mailadresse: '{cfg['from']}'. "
            "Erwartet z.B. name@domain.tld oder 'Name <name@domain.tld>', und die "
            "Adresse muss ein echtes Postfach auf dem SMTP-Account sein. Setzen unter "
            "System → Einstellungen → Mail (Absender) bzw. in der agent-eigenen "
            "smtp-Tool-Config — danach Dienst neu starten (Settings werden beim Start gelesen)."
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

    # Lazy: tools wird früh geladen — kein Top-Level-Import in communication (Zirkel).
    from hydrahive.communication.mail import _transport

    try:
        await asyncio.to_thread(_transport.send_message, cfg, msg)
    except Exception as e:
        return ToolResult.fail(f"Mail-Versand fehlgeschlagen: {e}")

    return ToolResult.ok(f"Mail an {to} gesendet", to=to, subject=subject)


TOOL = Tool(name="send_mail", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="mail")
