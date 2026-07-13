from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive import code_graph, code_graph_config
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes.media_projects import _authorize

router = APIRouter(prefix="/api/projects/{project_id}/code-graph", tags=["code-graph"])


class GraphConfig(BaseModel):
    scan_dirs: list[str] = Field(default_factory=list, max_length=50)


@router.get("/status")
def get_status(project_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _authorize(project_id, auth)
    return code_graph.status(project_id)


@router.get("/config")
def get_config(project_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _authorize(project_id, auth)
    return code_graph_config.get_config(project_id)


@router.get("/config/browse")
def browse_config(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    path: str = "",
) -> dict:
    """Unterverzeichnisse einer Ebene für die granulare Ordner-Auswahl."""
    _authorize(project_id, auth)
    return code_graph_config.browse_dirs(project_id, path)


@router.put("/config")
def put_config(project_id: str, body: GraphConfig, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _authorize(project_id, auth)
    return code_graph_config.set_config(project_id, body.scan_dirs)


@router.post("/build")
def build_graph(project_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _authorize(project_id, auth)
    try:
        return code_graph.build(project_id)
    except code_graph.CodeGraphError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, "code_graph_build_failed", reason=str(exc))
