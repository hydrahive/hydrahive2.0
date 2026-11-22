"""Server-zu-Server-Endpunkte für gekoppelte HydraHive-Server.

docs/specs/server-peering.md. KEIN Login, KEIN JWT: Jede Anfrage muss mit dem
Ed25519-Schlüssel eines aktiven Partners signiert sein (peer_protocol).
Zusätzlich lässt nginx /api/peering/ nur aus dem Tailnet durch.
Fehler nach außen nur als Code, Details stehen im eigenen Log.
"""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from hydrahive.federation import peer_protocol as proto

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/peering", tags=["peering"])

MAX_BODY = 1_048_576  # 1 MB


async def _read(request: Request, kind: str, *, id_field: str = "task_id") -> proto.Verified:
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
        id_field=id_field,
    )


def _rejected(exc: proto.PeerRejected) -> JSONResponse:
    logger.warning("Server-Kopplung: Anfrage abgelehnt (%s): %s", exc.code, exc)
    code = status.HTTP_403_FORBIDDEN
    if exc.code in ("peer_payload_invalid", "peer_payload_too_large"):
        code = status.HTTP_400_BAD_REQUEST
    elif exc.code == "peer_replay":
        code = status.HTTP_409_CONFLICT
    elif exc.code == "peer_rate_limited":
        code = status.HTTP_429_TOO_MANY_REQUESTS
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


@router.post("/catalog/push")
async def receive_catalog_push(request: Request):
    """Föderations-Katalog: Metadaten eines Clients annehmen (federation-catalog.md §Ablauf 3)."""
    from hydrahive.federation import catalog_hub

    peer_name = request.headers.get(proto.HEADER_PEER, "")[:24] or "?"
    try:
        verified = await _read(request, "catalog_push", id_field="msg_id")
        peer_name = verified.peer["name"]
        # DB-Arbeit (Transaktion mit Schreibsperre, bis 500 Upserts) nicht im Event-Loop
        return await asyncio.to_thread(catalog_hub.accept_push, verified.peer, verified.payload)
    except proto.PeerRejected as exc:
        detail = str(exc)[:200]  # Absender-Header kann vor der Signaturprüfung beliebig lang sein
        await asyncio.to_thread(
            catalog_hub.audit, peer_name, f"Push abgelehnt: {exc.code} ({detail})", severity="warning",
        )
        response = _rejected(exc)
        if isinstance(exc, catalog_hub.CatalogReplay):
            response = JSONResponse(
                status_code=response.status_code,
                content={"detail": {"code": exc.code, "params": {"last_seq": exc.last_seq}}},
            )
        return response


@router.post("/catalog/pull")
async def receive_catalog_pull(request: Request):
    """Gemeinsame Taskpflege: Client holt Einträge der anderen Instanzen ab
    (federation-shared-tasks.md §Nachricht catalog_pull). Antwort signiert."""
    from hydrahive.federation import catalog_hub, catalog_pull

    peer_name = request.headers.get(proto.HEADER_PEER, "")[:24] or "?"
    try:
        verified = await _read(request, "catalog_pull", id_field="msg_id")
        peer_name = verified.peer["name"]
        body, headers = await asyncio.to_thread(catalog_pull.accept_pull, verified.peer, verified.payload)
        return JSONResponse(content=body, headers=headers)
    except proto.PeerRejected as exc:
        await asyncio.to_thread(
            catalog_hub.audit, peer_name, f"Abholen abgelehnt: {exc.code} ({str(exc)[:200]})", severity="warning",
        )
        response = _rejected(exc)
        if isinstance(exc, catalog_hub.CatalogReplay):
            response = JSONResponse(
                status_code=response.status_code,
                content={"detail": {"code": exc.code, "params": {"last_seq": exc.last_seq}}},
            )
        return response


@router.post("/catalog/notify")
async def receive_catalog_notify(request: Request):
    """Gemeinsame Taskpflege: der eigene Hub stupst an (federation-shared-tasks.md
    §Anstupsen). Stößt gebündelt ein Abholen an, wartet nicht darauf.

    Jeder Fehler (auch Signatur, Frische, falscher Absender, Wiederholung) ergibt
    dasselbe ``404`` ohne Code; der Grund steht nur im Audit.
    """
    from hydrahive.federation import catalog_hub, catalog_notify_client

    peer_name = request.headers.get(proto.HEADER_PEER, "")[:24] or "?"
    try:
        verified = await _read(request, "catalog_notify", id_field="msg_id")
        peer_name = verified.peer["name"]
        await asyncio.to_thread(catalog_notify_client.check, verified.peer, verified.payload)
    except Exception as exc:  # jeder Fehler sieht nach außen gleich aus
        reason = getattr(exc, "reason", None) or getattr(exc, "code", None) or f"error:{type(exc).__name__}"
        await asyncio.to_thread(catalog_hub.audit, peer_name, f"Anstupsen abgelehnt: {reason}", severity="warning")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})
    catalog_notify_client.trigger()
    return {"ok": True}


@router.post("/catalog/read")
async def answer_catalog_read(request: Request):
    """Gemeinsame Taskpflege: Volltext für einen Client über den Hub (federation-shared-tasks.md
    §catalog_read). Jeder Fehler ergibt nach außen dasselbe 404, der Grund steht im Audit."""
    from hydrahive.federation import catalog_hub, catalog_read_hub

    peer_name = request.headers.get(proto.HEADER_PEER, "")[:24] or "?"
    try:
        verified = await _read(request, "catalog_read", id_field="msg_id")
        peer_name = verified.peer["name"]
        body, headers = await catalog_read_hub.answer_read(verified.peer, verified.payload)
        return JSONResponse(content=body, headers=headers)
    except Exception as exc:  # jeder Fehler sieht nach außen gleich aus
        reason = getattr(exc, "reason", None) or getattr(exc, "code", None) or f"error:{type(exc).__name__}"
        await asyncio.to_thread(catalog_hub.audit, peer_name, f"Lesen abgelehnt: {reason}", severity="warning")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})


@router.post("/catalog/fetch")
async def answer_catalog_fetch(request: Request):
    """Föderations-Katalog: Volltext an den eigenen Hub (federation-catalog.md §Ablauf 4).

    Jeder Fehler — auch Signatur, Frische, falscher Absender — ergibt dasselbe
    ``404`` ohne Code; der Grund steht nur im Audit.
    """
    from hydrahive.federation import catalog_hub, catalog_origin

    peer_name, payload = request.headers.get(proto.HEADER_PEER, "")[:24] or "?", None
    try:
        verified = await _read(request, "catalog_fetch", id_field="msg_id")
        peer_name, payload = verified.peer["name"], verified.payload
        body, headers = await asyncio.to_thread(catalog_origin.answer_fetch, verified.peer, verified.payload)
        return JSONResponse(content=body, headers=headers)
    except Exception as exc:  # jeder Fehler sieht nach außen gleich aus (Spec: immer 404)
        reason = getattr(exc, "reason", None) or getattr(exc, "code", None) or f"error:{type(exc).__name__}"
        await asyncio.to_thread(
            catalog_hub.audit, peer_name,
            f"Nachladen abgelehnt: {reason} ({catalog_origin.describe(payload)})", severity="warning",
        )
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})
