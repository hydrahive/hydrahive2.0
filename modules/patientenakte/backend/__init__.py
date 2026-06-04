"""Patientenakte-Modul — Backend.

register(ctx) →
  - Akte-Router         (/api/health/patientenakte/*)
  - FHIR-Import-Router  (/api/fhir/*)
  - eGA-Import-Router   (/api/ega/*)
  - Agent-Tool          query_fhir_data
  - additive Migrationen

Die Tabellen werden vom Core-Migrationsstand angelegt (akte_* via 023,
fhir_resources/ega_records via 021/022); die Modul-Migrationen sind
idempotente IF-NOT-EXISTS-Kopien (Selbst-Absicherung für frische
Installationen, No-op auf bestehenden DBs). Daten bleiben bei
Deinstallation immer erhalten.
"""
from __future__ import annotations

from .routes import router
from .fhir_routes import router as fhir_router
from .ega_routes import router as ega_router
from .fhir_tool import TOOL as fhir_tool


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_router(fhir_router)
    ctx.register_router(ega_router)
    ctx.register_tool(fhir_tool)
    ctx.register_migrations("migrations")
