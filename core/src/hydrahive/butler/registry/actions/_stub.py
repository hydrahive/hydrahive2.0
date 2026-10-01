"""Helper für Platzhalter-Aktionen ohne externen Adapter.

Die Aktion loggt nur ihre Parameter und meldet sich ehrlich als nicht verfügbar.
"""
from __future__ import annotations

import logging

from hydrahive.butler.registry import ActionResult, NOT_IMPLEMENTED_DETAIL

logger = logging.getLogger(__name__)


def stub_result(label: str, params: dict) -> ActionResult:
    logger.info("[butler-stub] %s params=%s", label, params)
    return ActionResult(ok=False, detail=NOT_IMPLEMENTED_DETAIL)
