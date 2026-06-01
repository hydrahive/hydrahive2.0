"""IMAP-Polling: liefert neue (ungesehene, nicht-dedupte) Mails.

Portiert aus HydraHive1 `mail_watcher._poll_imap`. Synchron — der Watcher ruft
es via `asyncio.to_thread` auf. Liefert reine Daten (`MailMessage`), keine
Seiteneffekte; Dedup-State hält der Aufrufer.
"""
from __future__ import annotations

import email
import imaplib
import logging
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.utils import parseaddr

logger = logging.getLogger(__name__)

_MAX_PER_POLL = 50
_BODY_BUDGET = 4000


@dataclass
class MailMessage:
    message_id: str
    from_addr: str
    from_name: str
    to: str
    subject: str
    date: str
    body: str


def _decode(raw: str) -> str:
    if not raw:
        return ""
    try:
        return str(make_header(decode_header(raw)))
    except Exception:
        return raw


def _split_from(raw_from: str) -> tuple[str, str]:
    name, addr = parseaddr(raw_from)
    return (addr or raw_from), (name or addr or raw_from)


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset("utf-8") or "utf-8", errors="replace"
                    )
                except Exception:
                    continue
        return ""
    try:
        return msg.get_payload(decode=True).decode(
            msg.get_content_charset("utf-8") or "utf-8", errors="replace"
        )
    except Exception:
        return ""


def poll_unseen(cfg: dict, folder: str, seen: set[str]) -> list[MailMessage]:
    """Holt UNSEEN-Mails aus `folder`, filtert bereits gesehene Message-IDs raus."""
    host = cfg.get("imap_host", "")
    user = cfg.get("imap_user", "")
    password = cfg.get("imap_password", "")
    if not host or not user or not password:
        logger.debug("mail_watcher: IMAP nicht konfiguriert (host/user/password fehlt)")
        return []

    port = int(cfg.get("imap_port", 993))
    out: list[MailMessage] = []
    conn = None
    try:
        conn = imaplib.IMAP4_SSL(host, port)
        conn.login(user, password)
        conn.select(folder, readonly=True)
        typ, data = conn.search(None, "UNSEEN")
        if typ != "OK" or not data or not data[0]:
            return []
        for mid in data[0].split()[-_MAX_PER_POLL:]:
            typ, msg_data = conn.fetch(mid, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            msg_id = (msg.get("Message-ID") or "").strip() or f"noid-{mid.decode()}"
            if msg_id in seen:
                continue
            addr, name = _split_from(_decode(msg.get("From", "")))
            out.append(MailMessage(
                message_id=msg_id,
                from_addr=addr,
                from_name=name,
                to=_decode(msg.get("To", "")),
                subject=_decode(msg.get("Subject", "")),
                date=msg.get("Date", ""),
                body=_extract_body(msg)[:_BODY_BUDGET],
            ))
    except imaplib.IMAP4.error as e:
        logger.warning("mail_watcher IMAP-Fehler: %s", e)
    except Exception as e:
        logger.warning("mail_watcher Poll-Fehler: %s", e)
    finally:
        if conn is not None:
            try:
                conn.logout()
            except Exception:
                pass
    return out
