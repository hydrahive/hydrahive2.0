"""Geräte-Router der Module einhängen (docs/specs/mining-modul.md §E0).

Getrennt von ``mount_module_routers`` (main.py), damit die login-geschützten
Modul-Routen und die Geräte-Routen nie unter demselben Präfix landen:

- ``/api/modules/<id>/…``        → Nutzer-Login + Capability ``module.<id>``
- ``/api/module-device/<id>/…``  → Prüfung des Moduls (``auth``) + Rate-Limit

Reihenfolge der Dependencies: zuerst das Rate-Limit, dann ``auth`` — so zählen
auch fehlgeschlagene Versuche und Token-Durchprobieren bleibt gebremst.
"""
from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, Request, status

from hydrahive.api.middleware.client_ip import client_ip
from hydrahive.api.middleware.errors import coded
from hydrahive.api.middleware.inbound_ratelimit import check_rate
from hydrahive.modules.registry import REGISTRY

logger = logging.getLogger(__name__)

DEVICE_PREFIX = "/api/module-device"
# Anfragen je Client-IP und Minute über alle Geräte-Routen eines Moduls.
# 20 Rigs hinter einer NAT-IP × alle 30 s = 40/min → genug Luft.
DEVICE_RATE_LIMIT = 240


def _rate_limit_for(module_id: str):
    def _dep(request: Request) -> None:
        allowed, retry_after = check_rate(
            f"module-device:{module_id}:{client_ip(request)}", limit=DEVICE_RATE_LIMIT,
        )
        if not allowed:
            raise coded(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited", retry_after=retry_after)

    _dep.__name__ = f"device_rate_limit[{module_id}]"
    return _dep


def mount_device_routers(target_app: FastAPI) -> None:
    """Hängt die Geräte-Router aller geladenen Module ein. Fehler pro Modul isoliert."""
    for entry in REGISTRY.values():
        if not (entry.loaded and entry.ctx):
            continue
        mid = entry.manifest.id
        for router, auth in entry.ctx.device_routers:
            try:
                target_app.include_router(
                    router, prefix=f"{DEVICE_PREFIX}/{mid}",
                    dependencies=[Depends(_rate_limit_for(mid)), Depends(auth)],
                )
            except Exception as exc:  # noqa: BLE001 — ein Modul darf den Start nicht abbrechen
                logger.error("Modul '%s': Geräte-Router fehlgeschlagen — übersprungen: %s", mid, exc)
