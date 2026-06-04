"""Patientenakte-Modul — Backend.

register(ctx) →
  - Akte-Router          (/api/modules/patientenakte/akte/*)
  - FHIR-Import-Router   (/api/modules/patientenakte/fhir/*)
  - eGA-Import-Router    (/api/modules/patientenakte/ega/*)
  - Apple-Health-Router  (/api/modules/patientenakte/health-data/*)  ← Ingest + Anzeige
  - Agent-Tools          query_fhir_data, query_health_data
  - additive Migrationen

Tabellen werden vom Core-Migrationsstand angelegt (akte_* 023, fhir/ega 021/022,
health 015/016/020); die Modul-Migrationen sind idempotente IF-NOT-EXISTS-Kopien
(Selbst-Absicherung für frische Installationen, No-op auf bestehenden DBs).
Daten bleiben bei Deinstallation immer erhalten. Die 2 Health-Settings
(health_api_key, health_ingest_user) bleiben Core-Config; das Modul liest sie.
"""
from __future__ import annotations

from .routes import router
from .fhir_routes import router as fhir_router
from .ega_routes import router as ega_router
from .health_routes import router as health_router
# Tool-Submodule importieren (NICHT `from .fhir_tool import TOOL as fhir_tool` — das
# würde das gleichnamige Submodul backend.fhir_tool überschatten und `import
# backend.fhir_tool` das Tool-Objekt statt des Moduls liefern lassen).
from . import fhir_tool, health_tool


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_router(fhir_router)
    ctx.register_router(ega_router)
    ctx.register_router(health_router)
    ctx.register_tool(fhir_tool.TOOL)
    ctx.register_tool(health_tool.TOOL)
    ctx.register_migrations("migrations")
