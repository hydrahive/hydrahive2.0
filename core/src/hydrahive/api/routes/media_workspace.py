from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, model_validator

from hydrahive import media_export, media_workspace
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes.media_projects import _authorize

router = APIRouter(prefix="/api/projects/{project_id}/media-projects/{media_slug}", tags=["media-workspace"])


class Shot(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=20_000)
    duration: float = Field(default=5, ge=0.1, le=3600)
    camera: str = Field(default="", max_length=200)
    character_ids: list[str] = Field(default_factory=list, max_length=100)
    asset_ids: list[str] = Field(default_factory=list, max_length=100)
    dialogue: str = Field(default="", max_length=20_000)


class Scene(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=20_000)
    shots: list[Shot] = Field(default_factory=list, max_length=500)


class Act(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(default="", max_length=200)
    scenes: list[Scene] = Field(default_factory=list, max_length=500)


class Screenplay(BaseModel):
    title: str = Field(default="", max_length=200)
    logline: str = Field(default="", max_length=10_000)
    acts: list[Act] = Field(default_factory=list, max_length=100)


class AgentContext(BaseModel):
    note: str = Field(default="", max_length=50_000)
    active_scene_id: str | None = Field(default=None, max_length=100)
    asset_ids: list[str] = Field(default_factory=list, max_length=100)
    prompt_draft: str = Field(default="", max_length=100_000)


class Clip(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    asset_id: str = Field(..., min_length=1, max_length=100)
    start: float = Field(ge=0, le=86_400)
    duration: float = Field(gt=0, le=86_400)
    source_in: float = Field(default=0, ge=0, le=86_400)
    volume: float = Field(default=1, ge=0, le=4)


class Track(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(default="", max_length=200)
    kind: Literal["video", "voice", "music", "audio"]
    muted: bool = False
    clips: list[Clip] = Field(default_factory=list, max_length=2000)


class CutPoint(BaseModel):
    """A/B-Roll-Schnittpunkt: schaltet den Output zwischen den Video-Spuren um.

    ``effect`` + ``duration`` beschreiben den Übergang: ``cut`` ist der
    Hartschnitt (Dauer ignoriert), sonst wird über ``duration`` Sekunden
    zentriert um ``time`` übergeblendet.
    """

    id: str = Field(..., min_length=1, max_length=100)
    time: float = Field(ge=0, le=86_400)
    effect: Literal["cut", "crossfade", "wipe", "fade-black"] = "cut"
    duration: float = Field(default=0, ge=0, le=30)


class Timeline(BaseModel):
    fps: int = Field(default=25, ge=1, le=120)
    width: int = Field(default=1920, ge=16, le=7680)
    height: int = Field(default=1080, ge=16, le=4320)
    tracks: list[Track] = Field(default_factory=list, max_length=100)
    cut_points: list[CutPoint] = Field(default_factory=list, max_length=2000)

    @model_validator(mode="after")
    def unique_ids(self):
        track_ids = [track.id for track in self.tracks]
        clip_ids = [clip.id for track in self.tracks for clip in track.clips]
        cut_ids = [cp.id for cp in self.cut_points]
        if (
            len(track_ids) != len(set(track_ids))
            or len(clip_ids) != len(set(clip_ids))
            or len(cut_ids) != len(set(cut_ids))
        ):
            raise ValueError("IDs müssen eindeutig sein")
        return self


def _run(project_id: str, auth: tuple[str, str], action):
    _authorize(project_id, auth)
    try:
        return action()
    except FileNotFoundError:
        raise coded(status.HTTP_404_NOT_FOUND, "media_project_not_found")


@router.get("/screenplay")
def get_screenplay(project_id: str, media_slug: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    return _run(project_id, auth, lambda: media_workspace.screenplay(project_id, media_slug))


@router.put("/screenplay")
def put_screenplay(project_id: str, media_slug: str, body: Screenplay, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    return _run(project_id, auth, lambda: media_workspace.save_screenplay(project_id, media_slug, body.model_dump()))


@router.get("/agent-context")
def get_agent_context(project_id: str, media_slug: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    return _run(project_id, auth, lambda: media_workspace.agent_context(project_id, media_slug))


@router.put("/agent-context")
def put_agent_context(project_id: str, media_slug: str, body: AgentContext, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    return _run(project_id, auth, lambda: media_workspace.save_agent_context(project_id, media_slug, body.model_dump()))


@router.get("/timeline")
def get_timeline(project_id: str, media_slug: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    return _run(project_id, auth, lambda: media_workspace.timeline(project_id, media_slug))


@router.put("/timeline")
def put_timeline(project_id: str, media_slug: str, body: Timeline, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    return _run(project_id, auth, lambda: media_workspace.save_timeline(project_id, media_slug, body.model_dump()))


@router.post("/timeline/export")
def export_timeline(project_id: str, media_slug: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _authorize(project_id, auth)
    try:
        return media_export.export(project_id, media_slug)
    except FileNotFoundError:
        raise coded(status.HTTP_404_NOT_FOUND, "media_project_or_asset_not_found")
    except media_export.MediaExportError:
        raise coded(status.HTTP_400_BAD_REQUEST, "media_export_failed")
