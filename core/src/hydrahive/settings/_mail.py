"""Mail-Watcher-Settings (Schicht 1: eine globale Mailbox, einem User zugeordnet).

Env-getrieben wie die übrigen Communication-Settings. IMAP zum Empfangen,
SMTP zum Antworten. `mail_owner_username` bestimmt, wessen Butler-Flows /
Master-Agent eingehende Mails verarbeiten.
"""
from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path


def _flag(name: str, default: str) -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes")


class _MailMixin:
    @cached_property
    def mail_enabled(self) -> bool:
        return _flag("HH_MAIL_ENABLED", "0")

    @cached_property
    def mail_owner_username(self) -> str:
        return os.environ.get("HH_MAIL_OWNER", "admin").strip() or "admin"

    @cached_property
    def mail_poll_interval(self) -> int:
        return int(os.environ.get("HH_MAIL_POLL_INTERVAL", "60"))

    @cached_property
    def mail_seen_ids(self) -> Path:
        return self.data_dir / "mail" / "seen_ids.json"

    @cached_property
    def mail_imap_host(self) -> str:
        return os.environ.get("HH_MAIL_IMAP_HOST", "").strip()

    @cached_property
    def mail_imap_port(self) -> int:
        return int(os.environ.get("HH_MAIL_IMAP_PORT", "993"))

    @cached_property
    def mail_imap_user(self) -> str:
        return os.environ.get("HH_MAIL_IMAP_USER", "").strip()

    @cached_property
    def mail_imap_password(self) -> str:
        return os.environ.get("HH_MAIL_IMAP_PASSWORD", "")

    @cached_property
    def mail_imap_folder(self) -> str:
        return os.environ.get("HH_MAIL_IMAP_FOLDER", "INBOX").strip() or "INBOX"

    @cached_property
    def mail_smtp_host(self) -> str:
        return os.environ.get("HH_MAIL_SMTP_HOST", "").strip()

    @cached_property
    def mail_smtp_port(self) -> int:
        return int(os.environ.get("HH_MAIL_SMTP_PORT", "587"))

    @cached_property
    def mail_smtp_user(self) -> str:
        return os.environ.get("HH_MAIL_SMTP_USER", "").strip()

    @cached_property
    def mail_smtp_password(self) -> str:
        return os.environ.get("HH_MAIL_SMTP_PASSWORD", "")

    @cached_property
    def mail_smtp_use_tls(self) -> bool:
        return _flag("HH_MAIL_SMTP_TLS", "1")

    @cached_property
    def mail_from(self) -> str:
        return os.environ.get("HH_MAIL_FROM", "").strip() or self.mail_smtp_user
