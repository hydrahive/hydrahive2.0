"""VM-Routes-Aggregator.

Bündelt die 5 Sub-Router (lifecycle / snapshots / imports / isos / vnc) zu
einem `router` damit api/main.py weiterhin nur einen Include-Call braucht.
Alle Sub-Router haben `prefix="/api/vms"` — FastAPI mergt das ohne Konflikt.
"""
from __future__ import annotations

from fastapi import APIRouter

from hydrahive.api.routes.vms_imports import router as _imports_router
from hydrahive.api.routes.vms_isos import router as _isos_router
from hydrahive.api.routes.vms_lifecycle import router as _lifecycle_router
from hydrahive.api.routes.vms_ops import router as _ops_router
from hydrahive.api.routes.vms_snapshots import router as _snapshots_router
from hydrahive.api.routes.vms_vnc import router as _vnc_router

router = APIRouter()
router.include_router(_lifecycle_router)
router.include_router(_ops_router)
router.include_router(_snapshots_router)
router.include_router(_imports_router)
router.include_router(_isos_router)
router.include_router(_vnc_router)
