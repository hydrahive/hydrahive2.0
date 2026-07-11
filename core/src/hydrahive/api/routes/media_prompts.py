from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from hydrahive import media_prompts
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes.media_projects import _authorize

router = APIRouter(prefix="/api/projects/{project_id}/media-projects/{media_slug}/prompts", tags=["media-prompts"])
PromptType = Literal["general", "image", "video", "music", "voice", "storyboard"]
PromptStatus = Literal["draft", "executed", "archived"]


class PromptCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
    type: PromptType
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(default="", max_length=100_000)
    model: str = Field(default="", max_length=200)
    asset_refs: list[str] = Field(default_factory=list, max_length=100)


class PromptUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, max_length=100_000)
    model: str | None = Field(default=None, max_length=200)
    status: PromptStatus | None = None
    asset_refs: list[str] | None = Field(default=None, max_length=100)
    result_refs: list[str] | None = Field(default=None, max_length=100)


def _error(exc: Exception):
    if isinstance(exc, FileNotFoundError):
        return coded(status.HTTP_404_NOT_FOUND, "media_project_or_prompt_not_found")
    if isinstance(exc, FileExistsError):
        return coded(status.HTTP_409_CONFLICT, "media_prompt_exists")
    return coded(status.HTTP_400_BAD_REQUEST, "invalid_media_prompt")


@router.get("")
def list_prompts(project_id: str, media_slug: str, auth: Annotated[tuple[str, str], Depends(require_auth)], prompt_type: PromptType | None = Query(default=None, alias="type")) -> list[dict]:
    _authorize(project_id, auth)
    try:
        return media_prompts.list_all(project_id, media_slug, prompt_type)
    except (FileNotFoundError, media_prompts.MediaPromptError) as exc:
        raise _error(exc)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_prompt(project_id: str, media_slug: str, body: PromptCreate, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _authorize(project_id, auth)
    try:
        return media_prompts.create(project_id, media_slug, body.type, body.slug, body.title, body.body, model=body.model, asset_refs=body.asset_refs)
    except (FileNotFoundError, FileExistsError, media_prompts.MediaPromptError) as exc:
        raise _error(exc)


@router.get("/{prompt_type}/{slug}")
def get_prompt(project_id: str, media_slug: str, prompt_type: PromptType, slug: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _authorize(project_id, auth)
    try:
        result = media_prompts.get(project_id, media_slug, prompt_type, slug)
    except (FileNotFoundError, media_prompts.MediaPromptError) as exc:
        raise _error(exc)
    if result is None:
        raise coded(status.HTTP_404_NOT_FOUND, "media_prompt_not_found")
    return result


@router.patch("/{prompt_type}/{slug}")
def update_prompt(project_id: str, media_slug: str, prompt_type: PromptType, slug: str, body: PromptUpdate, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _authorize(project_id, auth)
    try:
        return media_prompts.update(project_id, media_slug, prompt_type, slug, **body.model_dump(exclude_unset=True))
    except (FileNotFoundError, media_prompts.MediaPromptError) as exc:
        raise _error(exc)


@router.delete("/{prompt_type}/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(project_id: str, media_slug: str, prompt_type: PromptType, slug: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> None:
    _authorize(project_id, auth)
    try:
        deleted = media_prompts.delete(project_id, media_slug, prompt_type, slug)
    except (FileNotFoundError, media_prompts.MediaPromptError) as exc:
        raise _error(exc)
    if not deleted:
        raise coded(status.HTTP_404_NOT_FOUND, "media_prompt_not_found")
