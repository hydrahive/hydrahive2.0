"""Patientenakte (ePA-light) — strukturierte, schreibbare Multi-Patient-Akte."""
from __future__ import annotations

from hydrahive.patientenakte.schema import COMMON_FIELDS, ENTITIES, EntitySpec

__all__ = ["ENTITIES", "EntitySpec", "COMMON_FIELDS"]
