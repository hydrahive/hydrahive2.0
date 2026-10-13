"""Admin-API: Ort des System-Archivs wechseln (docs/specs/archiv-system.md, Etappe 1b).

Kein freies Pfadfeld: Auswahl nur aus der Platten-Liste (archive/disks.py) plus „default“. Umzug im Hintergrund
(archive/move_job.py), Fortschritt im Status. Darf HydraHive auf einer Platte nicht schreiben, richtet der
Root-Runner sie über eine feste Anfrage ein.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._addon_request import request_prepare_archive
from hydrahive.archive import disks, location, move, move_job

router = APIRouter(prefix="/api/admin/archive", tags=["admin"], dependencies=[Depends(require_admin)])

_ID = re.compile(r"^(default|[0-9a-f]{12})$")


class MoveRequest(BaseModel):
    location: str


def _entries() -> list[dict]:
    current = location.archive_root().resolve()
    default = location.default_root()
    out = [{"id": "default", "kind": "default", "path": str(default), "mount": "", "device": "", "fstype": "",
            "size_bytes": 0, "free_bytes": move._free_bytes(default), "writable": True}]
    out += [{**d, "kind": "disk"} for d in disks.list_disks()]
    for e in out:
        e["current"] = Path(e["path"]).resolve() == current
        e["problems"] = [] if e["current"] else move.check_target(Path(e["path"]))
    return out


def _lookup(loc: str) -> dict:
    if not _ID.match(loc):
        raise coded(status.HTTP_400_BAD_REQUEST, "archive_location_unknown")
    entry = next((e for e in _entries() if e["id"] == loc), None)
    if entry is None:
        raise coded(status.HTTP_404_NOT_FOUND, "archive_location_unknown")
    return entry


@router.get("/locations")
def archive_locations() -> dict:
    return {"entries": _entries()}


@router.post("/move", status_code=status.HTTP_202_ACCEPTED)
def archive_move(req: MoveRequest) -> dict:
    entry = _lookup(req.location)
    problems = ["same_location"] if entry["current"] else entry["problems"]
    if problems:
        raise coded(status.HTTP_409_CONFLICT, "archive_move_blocked", problems=problems)
    if not move_job.start(Path(entry["path"])):
        raise coded(status.HTTP_409_CONFLICT, "archive_move_blocked", problems=["move_running"])
    return {"started": True, "target": entry["path"]}


@router.post("/locations/{loc}/prepare", status_code=status.HTTP_202_ACCEPTED)
def archive_prepare(loc: str) -> dict:
    entry = _lookup(loc)
    if entry["kind"] != "disk":
        raise coded(status.HTTP_400_BAD_REQUEST, "archive_location_unknown")
    request_prepare_archive(entry["id"])
    return {"started": True}
