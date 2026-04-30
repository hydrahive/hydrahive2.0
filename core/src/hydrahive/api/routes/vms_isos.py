"""ISO-Library: list, upload, delete."""
from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._vms_helpers import is_admin
from hydrahive.vms import iso as vmiso

router = APIRouter(prefix="/api/vms", tags=["vms"])


@router.get("/isos/list")
def list_isos(_: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    return [asdict(i) for i in vmiso.list_isos(with_hash=False)]


@router.post("/isos/upload", status_code=201)
async def upload_iso(
    iso: Annotated[UploadFile, File()],
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    if not iso.filename:
        raise coded(status.HTTP_400_BAD_REQUEST, "iso_invalid_name", name="")
    try:
        result = await vmiso.save_upload_stream(iso.filename, iso)
    except vmiso.ISOError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    return asdict(result)


@router.delete("/isos/{filename}", status_code=204)
def delete_iso(
    filename: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    _, role = auth
    if not is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "vm_no_access")
    try:
        vmiso.delete_iso(filename)
    except vmiso.ISOError as e:
        raise coded(status.HTTP_404_NOT_FOUND, e.code, **e.params)
