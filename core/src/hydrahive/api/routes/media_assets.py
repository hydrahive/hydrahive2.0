from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive import media_assets
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes.media_projects import _authorize

router = APIRouter(prefix="/api/projects/{project_id}/media-projects/{media_slug}/assets", tags=["media-assets"])


class AssetCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
    kind: Literal["character", "style", "image", "video", "audio", "voice", "other"]
    source_project_id: str = Field(..., min_length=1, max_length=100)
    rel_path: str = Field(..., min_length=1, max_length=2000)
    label: str = Field(..., min_length=1, max_length=200)


def _source_authorize(source_project_id: str, auth: tuple[str, str]) -> None:
    _authorize(source_project_id, auth)


@router.get("")
def list_assets(project_id: str, media_slug: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    _authorize(project_id, auth)
    try:
        items = media_assets.list_all(project_id, media_slug)
        for source_id in {item["source_project_id"] for item in items}:
            _source_authorize(source_id, auth)
        return items
    except FileNotFoundError:
        raise coded(status.HTTP_404_NOT_FOUND, "media_project_not_found")
    except media_assets.MediaAssetError:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_media_asset")


@router.post("", status_code=status.HTTP_201_CREATED)
def create_asset(project_id: str, media_slug: str, body: AssetCreate, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _authorize(project_id, auth)
    _source_authorize(body.source_project_id, auth)
    try:
        return media_assets.create(project_id, media_slug, body.id, body.kind, body.source_project_id, body.rel_path, body.label)
    except FileExistsError:
        raise coded(status.HTTP_409_CONFLICT, "media_asset_exists")
    except FileNotFoundError:
        raise coded(status.HTTP_404_NOT_FOUND, "media_project_or_asset_not_found")
    except media_assets.MediaAssetError:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_media_asset")


@router.post("/{asset_id}/import")
def import_asset(project_id: str, media_slug: str, asset_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _authorize(project_id, auth)
    try:
        item = next((entry for entry in media_assets.list_all(project_id, media_slug) if entry["id"] == asset_id), None)
        if item is None:
            raise FileNotFoundError(asset_id)
        _source_authorize(item["source_project_id"], auth)
        return media_assets.import_copy(project_id, media_slug, asset_id)
    except FileNotFoundError:
        raise coded(status.HTTP_404_NOT_FOUND, "media_asset_not_found")
    except media_assets.MediaAssetError:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_media_asset")


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(project_id: str, media_slug: str, asset_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> None:
    _authorize(project_id, auth)
    try:
        if not media_assets.delete(project_id, media_slug, asset_id):
            raise coded(status.HTTP_404_NOT_FOUND, "media_asset_not_found")
    except media_assets.MediaAssetError:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_media_asset")
