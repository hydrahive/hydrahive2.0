"""Föderations-Katalog lesen (Hub): Liste und Detail (docs/specs/federation-catalog.md §API).

Eigener Router OHNE ``core.federation``: Die Katalog-Ansicht ist für jeden
angemeldeten Nutzer da (Spec AK 11). Sichtbarkeit: ein Nutzer sieht nur Einträge
mit seinem Nutzernamen als ``owner`` (gleicher Name über Server hinweg reicht,
Entscheidung Till 21.11.), Admins sehen alle. Einstellungen und Schalter bleiben
im Admin-Router ``federation_catalog.py``.
"""
from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.db import federation_catalog_mirror_view as mirror_view
from hydrahive.federation import catalog_detail, catalog_view

router = APIRouter(prefix="/api/federation/catalog", tags=["federation"])

_User = Annotated[AuthPrincipal, Depends(require_principal)]
_KINDS = ("task", "idea")


def _owners(user: AuthPrincipal) -> list[str] | None:
    return None if user.role == "admin" else [user.username]


@router.get("")
async def list_catalog(
    user: _User,
    instance: Annotated[list[str] | None, Query()] = None,
    project: Annotated[str | None, Query(max_length=200)] = None,
    status_: Annotated[list[str] | None, Query(alias="status")] = None,
    open_only: bool = False,
    kind: Annotated[str | None, Query(pattern="^(task|idea)$")] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=catalog_view.MAX_OFFSET)] = 0,
) -> dict:
    """Seite des Katalogs: Einträge der Partner + eigene des Hubs (``instance=local``),
    neueste Änderung zuerst. ``instance``/``status`` mehrfach möglich."""
    params = catalog_view.ListParams(
        instances=instance or None, project=project or None,
        statuses=[s for s in (status_ or []) if s][:12], open_only=open_only,
        kind=kind, q=q or None, limit=limit, offset=offset,
    )
    return await asyncio.to_thread(catalog_view.list_catalog, _owners(user), params)


@router.get("/mirror")
async def list_mirror(
    user: _User,
    instance: Annotated[list[str] | None, Query()] = None,
    project: Annotated[str | None, Query(max_length=200)] = None,
    status_: Annotated[list[str] | None, Query(alias="status")] = None,
    kind: Annotated[str | None, Query(pattern="^(task|idea)$")] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=mirror_view.MAX_OFFSET)] = 0,
) -> dict:
    """Kopie auf dem Client lesen (federation-shared-tasks.md §Oberfläche Cockpit), nur lesen.
    Gleiche Sichtbarkeit wie die Hub-Liste: eigener Nutzername, Admins alles.
    ``instance`` = ``origin_fp`` (mehrfach möglich). Antwort mit ``facets`` für die Filter."""
    owners = _owners(user)
    f = mirror_view.MirrorFilter(
        owners=owners, instances=[i for i in (instance or []) if i][:50] or None,
        project=project or None, statuses=[s for s in (status_ or []) if s][:12],
        kind=kind, q=q or None, limit=limit, offset=offset,
    )
    page = await asyncio.to_thread(mirror_view.list_page, f)
    page["facets"] = await asyncio.to_thread(mirror_view.facets, owners)
    return page


@router.get("/{peer_id}/{kind}/{item_id}")
async def open_catalog_item(
    peer_id: str, kind: str, item_id: str, user: _User,
    owner: Annotated[str | None, Query(max_length=128)] = None,
) -> dict:
    """Eintrag mit Volltext: live vom Ursprung (≤ 10 s) oder Snapshot/Metadaten mit
    „zuletzt gesehen“. ``peer_id=local`` = eigener Eintrag des Hubs (``owner`` nur
    für Admins, sonst immer der eigene Name). Nicht sichtbar/unbekannt → 404."""
    if kind not in _KINDS or len(peer_id) > 128 or len(item_id) > 128:
        raise coded(status.HTTP_404_NOT_FOUND, "catalog_item_not_found")
    is_admin = user.role == "admin"
    try:
        return await catalog_detail.open_item(
            peer_id, kind, item_id, user.username, is_admin=is_admin,
            owner=(owner if is_admin and owner else user.username),
        )
    except catalog_detail.NotVisible:
        raise coded(status.HTTP_404_NOT_FOUND, "catalog_item_not_found") from None
