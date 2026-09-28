"""Projekt-Webhook: Secret einsehen und neu erzeugen.

Der Butler-Endpoint ``POST /api/butler/webhooks/project/{id}`` verlangt das
Secret im Header ``X-Webhook-Secret``. Hier bekommt der Projekt-Admin den Wert
zu sehen und kann ihn austauschen. Die Projektliste liefert weiterhin nur
``has_webhook_secret`` (siehe ``projects/public_view.py``).
"""
from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import check_project_access
from hydrahive.projects import audit as project_audit
from hydrahive.projects import config as project_config

router = APIRouter(prefix="/api/projects", tags=["projects"])

WEBHOOK_PATH = "/api/butler/webhooks/project/{project_id}"


def _project_for_admin(project_id: str, auth: tuple[str, str]) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(p, *auth, required="admin")
    return p


def _view(project_id: str, secret: str) -> dict:
    return {
        "url_path": WEBHOOK_PATH.format(project_id=project_id),
        "secret": secret,
    }


@router.get("/{project_id}/webhook")
def get_webhook(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """URL-Pfad und aktuelles Secret — nur für Projekt-Admins."""
    p = _project_for_admin(project_id, auth)
    return _view(project_id, p.get("webhook_secret") or "")


@router.post("/{project_id}/webhook/rotate")
def rotate_webhook_secret(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Erzeugt ein neues Secret. Das alte gilt sofort nicht mehr."""
    _project_for_admin(project_id, auth)
    secret = secrets.token_urlsafe(32)
    project_config.update(project_id, webhook_secret=secret)
    project_audit.log(project_id, auth[0], "webhook_secret_rotated")
    return _view(project_id, secret)
