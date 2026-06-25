"""Prompt-Archiv HTTP-API — CRUD für gespeicherte Generierungs-Prompts.

Per-User mit Public-Toggle. user_id kommt aus dem JWT (require_auth → username).
Ownership wird bei Schreib-/Lösch-Operationen im DB-Modul geprüft (None/False
→ hier in 403/404 übersetzt). Frontend-Footer-Picker und Agent-Tools sprechen
dieselben Endpoints/dieselbe Tabelle.
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.db import prompt_archive as db_pa

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

Auth = Annotated[tuple[str, str], Depends(require_auth)]

Category = Literal["image", "music", "system", "video", "speech", "other"]


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class CreatePromptBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: Category = "other"
    prompt: str = Field(min_length=1, max_length=20000)
    style_anchor: str | None = Field(default=None, max_length=4000)
    model: str | None = Field(default=None, max_length=200)
    params: dict | None = None
    seed: int | None = None
    tags: list[str] | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=4000)
    sample_path: str | None = Field(default=None, max_length=1000)
    is_public: bool = False


class UpdatePromptBody(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category: Category | None = None
    prompt: str | None = Field(default=None, min_length=1, max_length=20000)
    style_anchor: str | None = Field(default=None, max_length=4000)
    model: str | None = Field(default=None, max_length=200)
    params: dict | None = None
    seed: int | None = None
    tags: list[str] | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=4000)
    sample_path: str | None = Field(default=None, max_length=1000)
    is_public: bool | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
def list_prompts(
    auth: Auth,
    category: Category | None = None,
    q: str | None = Query(default=None, max_length=200),
    include_public: bool = True,
) -> dict:
    username = auth[0]
    items = db_pa.list_for_user(
        username, category=category, query=q, include_public=include_public
    )
    return {"prompts": items, "count": len(items)}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_prompt(body: CreatePromptBody, auth: Auth) -> dict:
    username = auth[0]
    return db_pa.create(username, body.title, body.category, body.prompt,
                        style_anchor=body.style_anchor, model=body.model,
                        params=body.params, seed=body.seed, tags=body.tags,
                        notes=body.notes, sample_path=body.sample_path,
                        is_public=body.is_public)


@router.get("/{prompt_id}")
def get_prompt(prompt_id: str, auth: Auth) -> dict:
    username = auth[0]
    entry = db_pa.get(prompt_id)
    if not entry:
        raise HTTPException(status_code=404, detail="prompt_not_found")
    if entry["user_id"] != username and not entry["is_public"]:
        raise HTTPException(status_code=403, detail="not_your_prompt")
    return entry


@router.patch("/{prompt_id}")
def update_prompt(prompt_id: str, body: UpdatePromptBody, auth: Auth) -> dict:
    username = auth[0]
    fields = body.model_dump(exclude_none=True)
    updated = db_pa.update(prompt_id, username, **fields)
    if updated is None:
        # Eintrag fehlt oder gehört dem User nicht — nicht unterscheidbar nach außen.
        raise HTTPException(status_code=404, detail="prompt_not_found_or_not_owned")
    return updated


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(prompt_id: str, auth: Auth) -> None:
    username = auth[0]
    if not db_pa.delete(prompt_id, username):
        raise HTTPException(status_code=404, detail="prompt_not_found_or_not_owned")


@router.post("/{prompt_id}/use")
def mark_used(prompt_id: str, auth: Auth) -> dict:
    """use_count++ — wird aufgerufen wenn ein Prompt in den Chat geladen wird."""
    username = auth[0]
    entry = db_pa.get(prompt_id)
    if not entry:
        raise HTTPException(status_code=404, detail="prompt_not_found")
    if entry["user_id"] != username and not entry["is_public"]:
        raise HTTPException(status_code=403, detail="not_your_prompt")
    db_pa.bump_use_count(prompt_id)
    return {"ok": True}
