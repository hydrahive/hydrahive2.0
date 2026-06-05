"""Brücke: Modul-registrierte Butler-Subtypes in die Butler-Registry schieben.

Wird in der lifespan NACH load_builtins() aufgerufen, damit Module eigene
Trigger/Conditions/Actions beisteuern (SPEC: „weitere Trigger/Conditions/
Actions als Plugin nachrüstbar"). Nutzt die bestehende register_*-API.

Schutz: Core-Builtins werden NICHT überschrieben — ein Modul-Subtype, der mit
einem existierenden kollidiert, wird übersprungen + geloggt. Eine fehlerhafte
Registrierung bricht die anderen nicht (SPEC: „kaputtes Plugin bricht Core
nicht").
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from hydrahive.butler.registry import (
    ACTIONS,
    CONDITIONS,
    TRIGGERS,
    register_action,
    register_condition,
    register_trigger,
)
from hydrahive.modules.registry import REGISTRY

logger = logging.getLogger(__name__)


def register_module_butler_subtypes() -> int:
    """Speist alle Modul-Butler-Subtypes ein. Liefert die Anzahl registrierter."""
    count = 0
    for loaded in REGISTRY.values():
        if not (loaded.loaded and loaded.ctx):
            continue
        mid = loaded.manifest.id if loaded.manifest else loaded.name
        count += _register_group(mid, "Trigger", loaded.ctx.butler_triggers, TRIGGERS, register_trigger)
        count += _register_group(mid, "Condition", loaded.ctx.butler_conditions, CONDITIONS, register_condition)
        count += _register_group(mid, "Action", loaded.ctx.butler_actions, ACTIONS, register_action)
    return count


def _register_group(
    mid: str,
    kind: str,
    specs: list,
    existing: dict[str, Any],
    register_fn: Callable[[Any], None],
) -> int:
    count = 0
    for spec in specs:
        try:
            if spec.subtype in existing:
                logger.warning(
                    "Modul %s: Butler-%s '%s' kollidiert mit existierendem Subtype — übersprungen",
                    mid, kind, spec.subtype,
                )
                continue
            register_fn(spec)
            count += 1
            logger.info("Modul %s: Butler-%s '%s' registriert", mid, kind, spec.subtype)
        except Exception as e:
            logger.warning("Modul %s: Butler-%s konnte nicht registriert werden: %s", mid, kind, e)
    return count
