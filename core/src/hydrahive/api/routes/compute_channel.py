"""Authenticated WebSocket channel for read-only compute-agent reports."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from hydrahive.compute import channel

router = APIRouter(tags=["compute-agent"])
MAX_AGENT_MESSAGE_BYTES = 64 * 1024


@router.websocket("/api/compute/agent/connect")
async def connect_agent(websocket: WebSocket) -> None:
    node_id = websocket.headers.get("x-hydrahive-node-id", "")
    client_certificate = websocket.headers.get("x-hydrahive-client-cert", "")
    proxy_secret = websocket.headers.get("x-hydrahive-proxy-secret", "")
    try:
        channel.authenticate_node(node_id, client_certificate, proxy_secret)
    except channel.ProtocolError:
        await websocket.close(code=4403, reason="agent_identity_invalid")
        return

    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            if len(raw.encode("utf-8")) > MAX_AGENT_MESSAGE_BYTES:
                await websocket.close(code=4400, reason="agent_message_too_large")
                return
            try:
                message = channel.parse_message(raw)
                acknowledgement = channel.response_for_message(node_id, message)
            except channel.ProtocolError as exc:
                await websocket.send_json({"type": "error", "code": exc.code})
                await websocket.close(code=4400, reason=exc.code)
                return
            await websocket.send_json(acknowledgement)
    except WebSocketDisconnect:
        return
