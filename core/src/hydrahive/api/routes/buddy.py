"""Per-User Buddy: Auto-Create + State-Lookup + Slash-Commands.

Slash-Commands sind deterministisch (keine LLM-Roundtrips) — `/clear`,
`/remember`, `/model`, `/character`. Logik in `hydrahive.buddy.commands`.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.buddy import commands, get_or_create_buddy

router = APIRouter(prefix="/api/buddy", tags=["buddy"])


@router.get("/state")
def buddy_state(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    username, _ = auth
    return get_or_create_buddy(username)


def _user(auth: tuple[str, str]) -> str:
    return auth[0]


@router.post("/clear")
def buddy_clear(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    try:
        return commands.clear_session(_user(auth))
    except LookupError as e:
        raise coded(status.HTTP_404_NOT_FOUND, "buddy_not_found", message=str(e))


class RememberBody(BaseModel):
    text: str | None = Field(default=None, max_length=4000)
    name: str | None = Field(default=None, max_length=80)


@router.post("/remember")
def buddy_remember(
    body: RememberBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    try:
        return commands.remember(_user(auth), body.text, body.name)
    except LookupError as e:
        raise coded(status.HTTP_404_NOT_FOUND, "buddy_not_found", message=str(e))
    except ValueError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))


@router.get("/models")
def buddy_models(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    try:
        return commands.list_models(_user(auth))
    except LookupError as e:
        raise coded(status.HTTP_404_NOT_FOUND, "buddy_not_found", message=str(e))


class ModelBody(BaseModel):
    model: str = Field(min_length=1, max_length=200)


@router.post("/model")
def buddy_model(
    body: ModelBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    try:
        return commands.set_model(_user(auth), body.model)
    except LookupError as e:
        raise coded(status.HTTP_404_NOT_FOUND, "buddy_not_found", message=str(e))
    except ValueError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))


@router.post("/character")
def buddy_character(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    try:
        return commands.reroll_character(_user(auth))
    except LookupError as e:
        raise coded(status.HTTP_404_NOT_FOUND, "buddy_not_found", message=str(e))
