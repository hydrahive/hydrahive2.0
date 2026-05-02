from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._mcp_schemas import (
    McpServerCreate, McpServerUpdate, QuickAddRequest, annotate_status as _annotate_status,
)
from hydrahive.mcp import McpValidationError, config as mcp_config, manager as mcp_manager
from hydrahive.mcp import defaults as mcp_defaults

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/quick-add")
def quick_add_templates(_: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    """Template-Liste für die Quick-Add-Buttons im Frontend."""
    return mcp_defaults.TEMPLATES


@router.post("/quick-add", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def quick_add(req: QuickAddRequest) -> dict:
    template = mcp_defaults.get_template(req.template_id)
    if not template:
        raise coded(status.HTTP_404_NOT_FOUND, "mcp_template_not_found", template_id=req.template_id)
    rendered = mcp_defaults.render(template, req.inputs)
    try:
        return _annotate_status(mcp_config.create(
            server_id=req.server_id,
            name=rendered["name"],
            transport=rendered["transport"],
            command=rendered["command"],
            args=rendered["args"],
            env=rendered["env"],
            description=rendered["description"],
        ))
    except McpValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))


@router.get("/servers")
def list_servers(_: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    return [_annotate_status(s) for s in mcp_config.list_all()]


@router.post("/servers", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_server(req: McpServerCreate) -> dict:
    try:
        return _annotate_status(mcp_config.create(
            server_id=req.id, name=req.name, transport=req.transport,
            command=req.command, args=req.args, env=req.env,
            url=req.url, headers=req.headers,
            description=req.description, enabled=req.enabled,
        ))
    except McpValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))


@router.get("/servers/{server_id}")
def get_server(server_id: str, _: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    s = mcp_config.get(server_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "mcp_server_not_found")
    return _annotate_status(s)


@router.patch("/servers/{server_id}", dependencies=[Depends(require_admin)])
def update_server(server_id: str, req: McpServerUpdate) -> dict:
    changes = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        return _annotate_status(mcp_config.update(server_id, **changes))
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "mcp_server_not_found")
    except McpValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
async def delete_server(server_id: str) -> None:
    await mcp_manager.disconnect(server_id)
    if not mcp_config.delete(server_id):
        raise coded(status.HTTP_404_NOT_FOUND, "mcp_server_not_found")


@router.post("/servers/{server_id}/connect", dependencies=[Depends(require_admin)])
async def connect_server(server_id: str) -> dict:
    try:
        await mcp_manager.connect(server_id)
        tools = await mcp_manager.list_tools(server_id)
        return {
            "connected": True,
            "tools": [
                {"name": t.name, "description": t.description, "schema": t.schema}
                for t in tools
            ],
        }
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "mcp_server_not_found")
    except Exception as e:
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "mcp_connection_failed", message=str(e))


@router.post("/servers/{server_id}/disconnect", dependencies=[Depends(require_admin)])
async def disconnect_server(server_id: str) -> dict:
    ok = await mcp_manager.disconnect(server_id)
    return {"disconnected": ok}


@router.get("/servers/{server_id}/tools")
async def list_server_tools(
    server_id: str,
    _: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    if not mcp_config.get(server_id):
        raise coded(status.HTTP_404_NOT_FOUND, "mcp_server_not_found")
    try:
        tools = await mcp_manager.list_tools(server_id)
    except Exception as e:
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "mcp_tool_listing_failed", message=str(e))
    return [{"name": t.name, "description": t.description, "schema": t.schema} for t in tools]
