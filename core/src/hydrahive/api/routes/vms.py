"""VM-Routes-Aggregator.

Bündelt die 6 Sub-Router (lifecycle / snapshots / imports / isos / ops / vnc)
zu einem `router` damit api/main.py weiterhin nur einen Include-Call braucht.
Alle Sub-Router haben `prefix="/api/vms"` — FastAPI mergt das ohne Konflikt.

Reihenfolge ist wichtig: Sub-Router mit literalen Pfaden (`/import-jobs`,
`/isos`) müssen VOR denen mit `/{vm_id}`-Catch-All eingebunden werden, sonst
würde z. B. GET `/api/vms/import-jobs` auf `GET /api/vms/{vm_id}` matchen
und ein 404 `vm_not_found` liefern (FastAPI matcht in Definitions-Reihenfolge,
erstes Match gewinnt).
"""
from __future__ import annotations

from fastapi import APIRouter

from hydrahive.api.routes.vms_imports import router as _imports_router
from hydrahive.api.routes.vms_isos import router as _isos_router
from hydrahive.api.routes.vms_lifecycle import router as _lifecycle_router
from hydrahive.api.routes.vms_ops import router as _ops_router
from hydrahive.api.routes.vms_passthrough import router as _passthrough_router
from hydrahive.api.routes.vms_snapshots import router as _snapshots_router
from hydrahive.api.routes.vms_vnc import router as _vnc_router

router = APIRouter()
# Literale Pfade ZUERST — siehe Module-Docstring.
router.include_router(_imports_router)
router.include_router(_isos_router)
router.include_router(_passthrough_router)
# Danach die /{vm_id}-Routen.
router.include_router(_lifecycle_router)
router.include_router(_ops_router)
router.include_router(_snapshots_router)
router.include_router(_vnc_router)
