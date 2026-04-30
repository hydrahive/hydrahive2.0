"""Builtin-Trigger — Imports registrieren sich selbst beim Modul-Load."""
from __future__ import annotations

from hydrahive.butler.registry.triggers import (  # noqa: F401
    message_received, webhook_received, email_received,
    git_event_received, cron_fired,
)
