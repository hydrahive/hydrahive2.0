"""Dedup-State des Mail-Watchers: bereits verarbeitete Message-IDs.

IMAP wird readonly gepollt (Mails bleiben UNSEEN), darum merkt sich der Watcher
selbst, was er schon dispatcht hat — sonst würde jede Mail bei jedem Durchlauf
erneut beantwortet.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_MAX_SEEN = 2000


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def save_seen(path: Path, ids: set[str]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(sorted(ids)[-_MAX_SEEN:], ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        logger.warning("mail_watcher: seen-ids speichern fehlgeschlagen: %s", e)
