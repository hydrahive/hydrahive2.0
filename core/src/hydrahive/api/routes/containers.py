"""Container-Routes-Aggregator.

Bündelt CRUD- und Ops-Sub-Router damit api/main.py einen einzigen
Include-Call braucht.
"""
from __future__ import annotations

from fastapi import APIRouter

from hydrahive.api.routes.containers_crud import router as _crud_router
from hydrahive.api.routes.containers_ops import router as _ops_router

router = APIRouter()
router.include_router(_crud_router)
router.include_router(_ops_router)
