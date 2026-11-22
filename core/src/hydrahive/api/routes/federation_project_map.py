"""Gemeinsame Taskpflege: Projektzuordnung im Cockpit korrigieren
(docs/specs/federation-shared-tasks.md §Korrektur im Cockpit).

Jeder angemeldete Nutzer, nur eigene Zeilen: Die Zuordnung ist je Nutzer, denn nur er
sieht diese Einträge, und auch Nutzer ohne Admin-Rechte müssen sie korrigieren können.

- ``GET  /api/federation/catalog/project-map``: Ursprungsprojekte, von denen der Nutzer
  Einträge sieht, mit Anzahl, Einstellung (``auto``/``hidden``/project_id), Ergebnis und Grund.
- ``PUT  /api/federation/catalog/project-map``: ``{origin_fp, origin_project_id, target}``,
  ``target`` = ``auto`` | ``hidden`` | project_id. Ein Ziel-Projekt muss existieren und der
  Nutzer Mitglied sein (Admins: jedes), sonst 404 (kein Hinweis, ob es das Projekt gibt).
"""
from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.db import federation_catalog_project_map as map_db
from hydrahive.federation import catalog_project_map as pm
from hydrahive.projects import _members_model
from hydrahive.projects import config as project_config

router = APIRouter(prefix="/project-map", tags=["federation"])     # eingehängt in federation_catalog_view

_User = Annotated[AuthPrincipal, Depends(require_principal)]


class MapBody(BaseModel):
    origin_fp: str = Field(min_length=1, max_length=128)
    origin_project_id: str = Field(min_length=1, max_length=128)
    target: str = Field(min_length=1, max_length=128)        # auto | hidden | project_id


def _listing(user: AuthPrincipal) -> dict:
    manual = map_db.manual_rows(user.username)
    resolver = pm.Resolver(user.username, is_admin=user.role == "admin", manual=manual)
    out = []
    for e in map_db.origin_projects(user.username):
        a = resolver.resolve(e["origin_fp"], e["origin_project_id"], e["project_name"])
        out.append({**e, "setting": manual.get((e["origin_fp"], e["origin_project_id"]), "auto"),
                    "local_project_id": a.local_project_id, "hidden": a.hidden, "reason": a.reason})
    return {"origins": out}


@router.get("")
async def get_project_map(user: _User) -> dict:
    return await asyncio.to_thread(_listing, user)


def _apply(user: AuthPrincipal, body: MapBody) -> dict:
    target = body.target
    if target not in ("auto", pm.HIDDEN):
        project = project_config.get(target)
        if project is None or not (user.role == "admin" or _members_model.is_member(project, user.username)):
            raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    map_db.set_target(user.username, body.origin_fp, body.origin_project_id,
                      None if target == "auto" else target)
    return _listing(user)


@router.put("")
async def put_project_map(body: MapBody, user: _User) -> dict:
    return await asyncio.to_thread(_apply, user, body)
