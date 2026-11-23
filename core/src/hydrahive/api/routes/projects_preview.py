"""Testseite eines Projekts: Port, Status, Anmeldung (ziele/projekt-testumgebung.md §3 Weg B, §4; Etappe E1a).

- ``router`` (HydraHive-Login, Projekt-Leserecht): ``GET /api/projects/{id}/preview`` und ``POST …/preview/open``.
- ``gate_router`` (ohne Login, Bremse je Client-Adresse): ``/api/project-preview/login`` löst das Ticket ein und setzt
  das Cookie; ``/api/project-preview/auth`` ist das Prüf-Ziel für nginx auth_request (200 + ``X-Preview-Port`` nur für
  das passende Projekt). Die Durchreiche selbst (nginx) kommt mit Etappe E1b.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.client_ip import client_ip
from hydrahive.api.middleware.errors import coded
from hydrahive.api.middleware.inbound_ratelimit import check_rate
from hydrahive.projects import config as project_config
from hydrahive.projects import preview_auth, preview_port

router = APIRouter(prefix="/api/projects", tags=["projects"])
GATE_RATE_LIMIT = 240          # Anfragen je Client-Adresse und Minute (Seite + Bilder + Skripte laufen alle hier durch)


def _rate_limit(request: Request) -> None:
    allowed, retry_after = check_rate(f"project-preview:{client_ip(request)}", limit=GATE_RATE_LIMIT)
    if not allowed:
        raise coded(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited", retry_after=retry_after)


gate_router = APIRouter(prefix="/api/project-preview", tags=["projects"], dependencies=[Depends(_rate_limit)])


def _project(project_id: str, p: AuthPrincipal) -> dict:
    from hydrahive.api.routes._project_route_helpers import check_project_access
    project = project_config.get(project_id)
    if not project:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(project, p.username, p.role, "read")
    return project


def _port(project_id: str) -> int:
    try:
        return preview_port.ensure(project_id)
    except preview_port.PreviewPortError as exc:
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, exc.code) from None


@router.get("/{project_id}/preview")
def preview_status(project_id: str, p: Annotated[AuthPrincipal, Depends(require_principal)]) -> dict:
    _project(project_id, p)
    port = _port(project_id)
    return {"port": port, "running": preview_port.running(port)}


@router.post("/{project_id}/preview/open")
def preview_open(project_id: str, p: Annotated[AuthPrincipal, Depends(require_principal)]) -> dict:
    """Einmal-Ticket (60 s) für die Durchreiche. Den Link baut die Oberfläche (E1c) aus Ticket und Durchreiche."""
    _project(project_id, p)
    port = _port(project_id)
    return {"ticket": preview_auth.new_ticket(p.user_id, project_id), "expires_in": preview_auth.TICKET_TTL,
            "port": port}


@gate_router.get("/login")
def preview_login(t: Annotated[str, Query(min_length=1, max_length=128)]) -> Response:
    got = preview_auth.redeem(t)
    if got is None:
        raise coded(status.HTTP_401_UNAUTHORIZED, "project_preview_login_required")
    r = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    r.set_cookie(preview_auth.COOKIE, preview_auth.issue_cookie(*got), max_age=preview_auth.MAX_AGE, path="/",
                 httponly=True, secure=True, samesite="lax")
    return r


@gate_router.get("/auth")
def preview_check(
    hh_project_preview: Annotated[str | None, Cookie()] = None,
    x_preview_project: Annotated[str | None, Header(max_length=64)] = None,
) -> Response:
    """nginx fragt hier vor jeder Anfrage an die Testseite. ``X-Preview-Project`` setzt nginx aus der Adresse."""
    pid = preview_auth.project_from(hh_project_preview)
    if pid is None:
        raise coded(status.HTTP_401_UNAUTHORIZED, "project_preview_login_required")
    if not x_preview_project or x_preview_project != pid:
        raise coded(status.HTTP_403_FORBIDDEN, "project_preview_wrong_project")
    port = preview_port.stored(project_config.get(pid))
    if port is None:
        raise coded(status.HTTP_403_FORBIDDEN, "project_preview_wrong_project")
    return Response(status_code=status.HTTP_200_OK, headers={"X-Preview-Port": str(port)})
