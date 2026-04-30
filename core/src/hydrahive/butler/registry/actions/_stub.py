"""Helper für Phase-2-Stubs: Action loggt nur was sie tun würde,
Phase 4 verkabelt mit echten Channel/Email/Discord-Adaptern."""
from __future__ import annotations

import logging

from hydrahive.butler.registry import ActionResult

logger = logging.getLogger(__name__)


def stub_result(label: str, params: dict) -> ActionResult:
    logger.info("[butler-stub] %s params=%s", label, params)
    return ActionResult(ok=True, detail=f"stub:{label}")
