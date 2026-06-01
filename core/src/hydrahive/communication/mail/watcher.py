"""Mail-Watcher-Loop: pollt IMAP, dispatcht über den Channel-Router, antwortet per SMTP.

Eingehende Mail wird wie jede Channel-Nachricht durch `handle_incoming` geschickt
(Butler-Pass → sonst Master-Agent). Der Absender ist immer ein externer Kontakt
(`is_owner=False`) → die Sender-Rahmung/Datenschutz-Logik greift automatisch.
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.communication.base import IncomingEvent
from hydrahive.communication.mail import _seen, imap_poll, smtp_send
from hydrahive.communication.router import handle_incoming
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_STARTUP_DELAY = 15


def _mail_cfg() -> dict:
    return {
        "imap_host": settings.mail_imap_host,
        "imap_port": settings.mail_imap_port,
        "imap_user": settings.mail_imap_user,
        "imap_password": settings.mail_imap_password,
        "smtp_host": settings.mail_smtp_host,
        "smtp_port": settings.mail_smtp_port,
        "smtp_user": settings.mail_smtp_user,
        "smtp_password": settings.mail_smtp_password,
        "smtp_from": settings.mail_from,
        "smtp_use_tls": settings.mail_smtp_use_tls,
    }


async def _process(mail: imap_poll.MailMessage, cfg: dict) -> None:
    own = (cfg.get("smtp_from") or cfg.get("imap_user") or "").lower()
    if own and mail.from_addr.lower() == own:
        logger.debug("mail_watcher: Self-Mail von %s ignoriert (Loop-Schutz)", mail.from_addr)
        return

    event = IncomingEvent(
        channel="email",
        external_user_id=mail.from_addr,
        target_username=settings.mail_owner_username,
        text=mail.body,
        sender_name=mail.from_name or mail.from_addr,
        metadata={"is_owner": False, "is_group": False, "subject": mail.subject},
    )
    answer = await handle_incoming(event)
    if not answer:
        return

    subject = mail.subject if mail.subject.lower().startswith("re:") else f"Re: {mail.subject}"
    await asyncio.to_thread(
        smtp_send.send_reply, cfg,
        to=mail.from_addr, subject=subject, body=answer,
        in_reply_to=mail.message_id,
    )
    logger.info("mail_watcher: Antwort an %s gesendet", mail.from_addr)


async def run_loop(stop: asyncio.Event) -> None:
    await asyncio.sleep(_STARTUP_DELAY)
    folder = settings.mail_imap_folder
    seen_path = settings.mail_seen_ids
    interval = settings.mail_poll_interval
    logger.info("mail_watcher gestartet (Intervall %ds, Ordner %s)", interval, folder)

    while not stop.is_set():
        try:
            cfg = _mail_cfg()
            seen = _seen.load_seen(seen_path)
            mails = await asyncio.to_thread(imap_poll.poll_unseen, cfg, folder, seen)
            for mail in mails:
                seen.add(mail.message_id)
                try:
                    await _process(mail, cfg)
                except Exception as e:
                    logger.warning("mail_watcher: Verarbeitung von %s fehlgeschlagen: %s",
                                   mail.message_id, e)
            if mails:
                _seen.save_seen(seen_path, seen)
        except Exception as e:
            logger.warning("mail_watcher Loop-Fehler: %s", e)

        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass

    logger.info("mail_watcher beendet")
