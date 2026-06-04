"""Patientenakte-Modul — Backend.

register(ctx) → Router (/api/health/patientenakte/*) + additive Migration.
Die Akte-Tabellen werden vom Core-Migrationsstand 023 angelegt; die Modul-
Migration ist eine idempotente IF-NOT-EXISTS-Kopie (Selbst-Absicherung für
frische Installationen, No-op auf bestehenden DBs). Daten bleiben bei
Deinstallation immer erhalten.
"""
from __future__ import annotations

from .routes import router


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
