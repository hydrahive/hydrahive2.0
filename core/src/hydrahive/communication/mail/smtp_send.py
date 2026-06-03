"""SMTP-Versand für Mail-Antworten des Watchers.

Synchron — der Watcher ruft es via `asyncio.to_thread` auf. `in_reply_to`
setzt die Threading-Header, damit die Antwort im Mailclient am Original hängt.
"""
from __future__ import annotations

from email.message import EmailMessage

from hydrahive.communication.mail import _transport


def send_reply(cfg: dict, *, to: str, subject: str, body: str,
               in_reply_to: str | None = None) -> None:
    msg = EmailMessage()
    msg["From"] = cfg.get("smtp_from", "") or cfg.get("smtp_user", "")
    msg["To"] = to
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(body)

    _transport.send_message(
        {
            "host": cfg.get("smtp_host", ""),
            "port": cfg.get("smtp_port", 587),
            "user": cfg.get("smtp_user"),
            "password": cfg.get("smtp_password"),
            "use_tls": cfg.get("smtp_use_tls", True),
        },
        msg,
    )
