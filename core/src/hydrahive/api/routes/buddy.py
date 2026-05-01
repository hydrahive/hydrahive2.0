"""Per-User Buddy: Auto-Create + State-Lookup."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth
from hydrahive.buddy import get_or_create_buddy

router = APIRouter(prefix="/api/buddy", tags=["buddy"])


@router.get("/state")
def buddy_state(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    username, _ = auth
    return get_or_create_buddy(username)
