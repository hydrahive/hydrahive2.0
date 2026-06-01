from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query

from hydrahive.api.middleware.auth import require_auth
from hydrahive.agents import config as agents_config
from hydrahive.agents._paths import ensure_workspace
from hydrahive.workspace._paths import resolve_in_workspace, WorkspacePathError
from hydrahive.workspace._tree import list_dir, read_file

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


def _root_for(agent_id: str, auth: tuple[str, str]):
    username, role = auth
    agent = agents_config.get(agent_id)
    # 404 (nicht 403) wenn fremd — Existenz fremder Agents nicht leaken
    if not agent or (role != "admin" and agent.get("owner") != username):
        raise HTTPException(status_code=404, detail="agent_not_found")
    return ensure_workspace(agent)


@router.get("/tree")
def get_tree(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    agent_id: str = Query(...),
    path: str = Query(""),
) -> list[dict]:
    root = _root_for(agent_id, auth)
    try:
        abs_path = resolve_in_workspace(root, path)
    except WorkspacePathError:
        raise HTTPException(status_code=403, detail="path_outside_workspace")
    try:
        return list_dir(abs_path)
    except NotADirectoryError:
        raise HTTPException(status_code=400, detail="not_a_directory")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="not_found")


@router.get("/file")
def get_file(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    agent_id: str = Query(...),
    path: str = Query(...),
) -> dict:
    root = _root_for(agent_id, auth)
    try:
        abs_path = resolve_in_workspace(root, path)
    except WorkspacePathError:
        raise HTTPException(status_code=403, detail="path_outside_workspace")
    try:
        return {"path": path, "content": read_file(abs_path)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="file_not_found")
    except ValueError:
        raise HTTPException(status_code=413, detail="file_too_large")
