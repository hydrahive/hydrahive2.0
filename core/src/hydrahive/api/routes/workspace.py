from __future__ import annotations
import mimetypes
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_auth
from hydrahive.agents import config as agents_config
from hydrahive.agents._paths import ensure_workspace
from hydrahive.workspace._paths import resolve_in_workspace, WorkspacePathError
from hydrahive.workspace._tree import list_dir, read_file, write_file

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


class WriteBody(BaseModel):
    agent_id: str
    path: str
    content: str


@router.put("/file")
def put_file(
    body: WriteBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    root = _root_for(body.agent_id, auth)
    try:
        abs_path = resolve_in_workspace(root, body.path)
    except WorkspacePathError:
        raise HTTPException(status_code=403, detail="path_outside_workspace")
    write_file(abs_path, body.content)
    return {"ok": True}


@router.get("/raw")
def get_raw(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    agent_id: str = Query(...),
    path: str = Query(...),
) -> FileResponse:
    """Rohe Datei-Bytes (für Bild/Video/Audio-Viewer + Download)."""
    root = _root_for(agent_id, auth)
    try:
        abs_path = resolve_in_workspace(root, path)
    except WorkspacePathError:
        raise HTTPException(status_code=403, detail="path_outside_workspace")
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail="file_not_found")
    media_type = mimetypes.guess_type(abs_path.name)[0] or "application/octet-stream"
    # Workspace-Inhalt ist untrusted (Agenten schreiben autonom). Stored-XSS-Schutz
    # für aktiv renderbare Typen (SVG/HTML): FileResponse(filename=) setzt bereits
    # Content-Disposition: attachment; zusätzlich sandbox-CSP + nosniff. Direkte
    # Navigation wird damit sandboxed/heruntergeladen statt mit Scripts gerendert;
    # der Viewer holt die Bytes per Blob-Fetch und behält so den echten Content-Type.
    headers = {
        "Content-Security-Policy": "sandbox; default-src 'none'",
        "X-Content-Type-Options": "nosniff",
    }
    return FileResponse(abs_path, media_type=media_type, filename=abs_path.name, headers=headers)
