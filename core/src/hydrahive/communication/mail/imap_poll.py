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


def _parse(mid: bytes, raw: bytes) -> MailMessage:
    msg = email.message_from_bytes(raw)
    msg_id = (msg.get("Message-ID") or "").strip() or f"noid-{mid.decode()}"
    addr, name = _split_from(_decode(msg.get("From", "")))
    return MailMessage(
        message_id=msg_id,
        from_addr=addr,
        from_name=name,
        to=_decode(msg.get("To", "")),
        subject=_decode(msg.get("Subject", "")),
        date=msg.get("Date", ""),
        body=_extract_body(msg)[:_BODY_BUDGET],
    )


def fetch(cfg: dict, folder: str, *, criterion: str = "ALL",
          limit: int = _MAX_PER_POLL) -> list[MailMessage]:
    """Read-only-Fetch der letzten `limit` Mails, die `criterion` (ALL/UNSEEN…)
    matchen. Reine Daten, kein Dedup — Single Source für Watcher und read_mail."""
    host = cfg.get("imap_host", "")
    user = cfg.get("imap_user", "")
    password = cfg.get("imap_password", "")
    if not host or not user or not password:
        logger.debug("imap: nicht konfiguriert (host/user/password fehlt)")
        return []

    port = int(cfg.get("imap_port", 993))
    out: list[MailMessage] = []
    conn = None
    try:
        conn = imaplib.IMAP4_SSL(host, port)
        conn.login(user, password)
        conn.select(folder, readonly=True)
        typ, data = conn.search(None, criterion)
        if typ != "OK" or not data or not data[0]:
            return []
        for mid in data[0].split()[-limit:]:
            typ, msg_data = conn.fetch(mid, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            out.append(_parse(mid, msg_data[0][1]))
    except imaplib.IMAP4.error as e:
        logger.warning("imap IMAP-Fehler: %s", e)
    except Exception as e:
        logger.warning("imap Fetch-Fehler: %s", e)
    finally:
        if conn is not None:
            try:
                conn.logout()
            except (OSError, imaplib.IMAP4.error):
                pass  # Verbindung wird ohnehin verworfen — Logout-Fehler egal
    return out


def poll_unseen(cfg: dict, folder: str, seen: set[str]) -> list[MailMessage]:
    """Holt UNSEEN-Mails aus `folder`, filtert bereits gesehene Message-IDs raus."""
    return [m for m in fetch(cfg, folder, criterion="UNSEEN", limit=_MAX_PER_POLL)
            if m.message_id not in seen]
