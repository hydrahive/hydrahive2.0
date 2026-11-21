"""Registry der Katalog-Quellen (docs/specs/federation-catalog.md §Katalog-Quellen).

Module melden sich in `register(ctx)` mit `ctx.register_catalog_source(...)` an.
`collect_catalog_sources()` übernimmt sie beim Start (lifespan, nach load_all)
in `CATALOG_SOURCES`. Je `kind` höchstens eine Quelle: meldet ein zweites Modul
dieselbe Art an, wird es übersprungen und geloggt (wie butler_bridge bei
kollidierenden Subtypes). Der Kern liest Modultabellen nie direkt, sondern nur
über diese Quellen (ab Etappe 3: Push, Abgleich, Nachladen).
"""
from __future__ import annotations

import logging

from hydrahive.modules.context import CatalogSource
from hydrahive.modules.registry import REGISTRY

logger = logging.getLogger(__name__)

# kind → (module_id, Quelle)
CATALOG_SOURCES: dict[str, tuple[str, CatalogSource]] = {}


def collect_catalog_sources() -> int:
    """Übernimmt die Quellen aller geladenen Module. Idempotent (setzt neu)."""
    CATALOG_SOURCES.clear()
    for loaded in REGISTRY.values():
        if not (loaded.loaded and loaded.ctx):
            continue
        mid = loaded.manifest.id if loaded.manifest else loaded.name
        for source in getattr(loaded.ctx, "catalog_sources", []):
            owner = CATALOG_SOURCES.get(source.kind)
            if owner is not None:
                logger.warning(
                    "Modul %s: Katalog-Quelle '%s' schon von Modul %s angemeldet — übersprungen",
                    mid, source.kind, owner[0],
                )
                continue
            CATALOG_SOURCES[source.kind] = (mid, source)
            logger.info("Modul %s: Katalog-Quelle '%s' angemeldet", mid, source.kind)
    return len(CATALOG_SOURCES)


def get_source(kind: str) -> CatalogSource | None:
    entry = CATALOG_SOURCES.get(kind)
    return entry[1] if entry else None


def source_kinds() -> list[str]:
    return sorted(CATALOG_SOURCES)
