"""Einmalige, idempotente Migration: jedes Projekt bekommt ein Webhook-Secret.

Altprojekte ohne ``webhook_secret`` nahmen am Butler-Webhook jeden POST an
(Task 44fffa23). Beim Start wird für jedes Projekt ohne Secret eines erzeugt,
``webhook_secret_auto`` gesetzt (das Cockpit zeigt dazu einen Hinweis) und ein
Audit-Eintrag ``webhook_secret_generated`` geschrieben, ohne den Wert.
Ein zweiter Lauf ändert nichts mehr.
"""
from __future__ import annotations

import logging
import secrets

logger = logging.getLogger(__name__)

SYSTEM_USER = "system"


def has_secret(cfg: dict) -> bool:
    value = cfg.get("webhook_secret")
    return isinstance(value, str) and bool(value.strip())


def ensure_webhook_secrets() -> int:
    """Erzeugt fehlende Secrets. Gibt die Anzahl neu erzeugter zurück."""
    from hydrahive.projects import audit as project_audit
    from hydrahive.projects import config as project_config

    created = 0
    for cfg in project_config.list_all():
        if has_secret(cfg):
            continue
        project_id = cfg.get("id")
        if not project_id:
            continue
        try:
            project_config.update(
                project_id,
                webhook_secret=secrets.token_urlsafe(32),
                webhook_secret_auto=True,
            )
        except Exception:
            logger.warning("Webhook-Secret für Projekt %s nicht erzeugt", project_id, exc_info=True)
            continue
        project_audit.log(project_id, SYSTEM_USER, "webhook_secret_generated")
        created += 1
    if created:
        logger.info("Webhook-Secret automatisch erzeugt für %d Projekt(e)", created)
    return created
