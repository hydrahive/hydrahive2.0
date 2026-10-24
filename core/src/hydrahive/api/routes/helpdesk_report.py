"""Fehlerbericht des Hilfe-Assistenten (docs/plans/help-error-report.md).

- GET    /api/helpdesk/report-status    – Schalter, Mailkonto vorhanden?, darf der Nutzer es einrichten (Admin)?
- GET    /api/helpdesk/report/{id}      – eigenen Entwurf ansehen (ohne Mailkonto mit mailto-Link)
- POST   /api/helpdesk/report/{id}/send – senden (nur so – kein Werkzeug kann senden); ohne Mailkonto: mailto-Daten
- DELETE /api/helpdesk/report/{id}      – verwerfen
Fremde oder abgelaufene Entwürfe: 404. Schlägt der Versand fehl, bleibt der Entwurf erhalten.
"""
from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.helpdesk import _report, _report_send

router = APIRouter(prefix="/api/helpdesk", tags=["helpdesk"])
_Auth = Annotated[tuple[str, str], Depends(require_auth)]


@router.get("/report-status")
def report_status(auth: _Auth) -> dict:
    return {"enabled": _report.enabled(), "mail_account": _report_send.has_mail_account(),
            "can_setup": auth[1] == "admin"}


@router.get("/report/{rid}")
def get_report(rid: str, auth: _Auth) -> dict:
    d = _report.get(auth[0], rid)
    if not d:
        raise coded(status.HTTP_404_NOT_FOUND, "report_not_found")
    out = {**d, "to": _report.recipient()}
    if not _report_send.has_mail_account():         # ohne Mailkonto: fertiger mailto-Link, Entwurf bleibt
        m = _report_send.mailto(d)
        out.update(mailto=m["mailto"], truncated=m["truncated"])
    return out


@router.post("/report/{rid}/send")
async def send_report(rid: str, auth: _Auth) -> dict:
    if not _report.enabled():
        raise coded(status.HTTP_403_FORBIDDEN, "error_report_disabled")
    if not _report.get(auth[0], rid):
        raise coded(status.HTTP_404_NOT_FOUND, "report_not_found")
    mail = _report_send.has_mail_account()
    if mail:
        try:
            _report.check_limits(auth[0])
        except _report.RateLimited:
            raise coded(status.HTTP_429_TOO_MANY_REQUESTS, "error_report_rate_limited") from None
    try:
        draft = _report.take(auth[0], rid)
    except _report.ReportError:
        raise coded(status.HTTP_404_NOT_FOUND, "report_not_found") from None
    try:
        result = await asyncio.to_thread(_report_send.send, draft)
    except _report_send.SendFailed as e:
        _report.restore(auth[0], draft)          # Versand gescheitert → Entwurf zurück, Nutzer kann erneut senden
        raise coded(status.HTTP_502_BAD_GATEWAY, "error_report_send_failed", message=str(e)) from None
    if result.get("sent"):
        _report.note_sent(auth[0])
    return result


@router.delete("/report/{rid}", status_code=status.HTTP_204_NO_CONTENT)
def discard_report(rid: str, auth: _Auth) -> Response:
    if not _report.discard(auth[0], rid):
        raise coded(status.HTTP_404_NOT_FOUND, "report_not_found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
