"""Server-zu-Server-Endpunkte für gekoppelte HydraHive-Server.

docs/specs/server-peering.md. KEIN Login, KEIN JWT: Jede Anfrage muss mit dem
Ed25519-Schlüssel eines aktiven Partners signiert sein (peer_protocol).
Zusätzlich lässt nginx /api/peering/ nur aus dem Tailnet durch.
Fehler nach außen nur als Code, Details stehen im eigenen Log.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from hydrahive.federation import peer_protocol as proto

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/peering", tags=["peering"])

MAX_BODY = 1_048_576  # 1 MB


async def _read(request: Request, kind: str) -> proto.Verified:
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_BODY:
        raise proto.PeerRejected("peer_payload_too_large")
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise proto.PeerRejected("peer_payload_too_large")
    try:
        payload = json.loads(raw)
    except ValueError:
        raise proto.PeerRejected("peer_payload_invalid", "kein JSON")
    if not isinstance(payload, dict):
        raise proto.PeerRejected("peer_payload_invalid", "kein Objekt")
    return proto.verify_incoming(
        request.headers.get(proto.HEADER_PEER, ""),
        request.headers.get(proto.HEADER_SIGNATURE, ""),
        payload,
        kind,
    )


def _rejected(exc: proto.PeerRejected) -> JSONResponse:
    logger.warning("Server-Kopplung: Anfrage abgelehnt (%s): %s", exc.code, exc)
    code = status.HTTP_403_FORBIDDEN
    if exc.code in ("peer_payload_invalid", "peer_payload_too_large"):
        code = status.HTTP_400_BAD_REQUEST
    elif exc.code == "peer_replay":
        code = status.HTTP_409_CONFLICT
    elif exc.code == "peer_local_failed":
        code = status.HTTP_502_BAD_GATEWAY
    return JSONResponse(status_code=code, content={"detail": {"code": exc.code}})


@router.post("/tasks", status_code=status.HTTP_202_ACCEPTED)
async def receive_task(request: Request):
    from hydrahive.federation.peer_inbound import accept_task

    try:
        verified = await _read(request, "task")
        await accept_task(verified.peer, verified.payload)
    except proto.PeerRejected as exc:
        return _rejected(exc)
    return {"accepted": verified.payload["task_id"]}


@router.post("/replies", status_code=status.HTTP_202_ACCEPTED)
async def receive_reply(request: Request):
    from hydrahive.federation.peer_outbound import resolve_reply

    try:
        verified = await _read(request, "reply")
    except proto.PeerRejected as exc:
        return _rejected(exc)
    if not resolve_reply(verified.peer, verified.payload):
        return _rejected(proto.PeerRejected("peer_reply_unknown", "keine wartende Anfrage"))
    return {"ok": True}
