"""CRUD-Routes für SMB-Mounts — gehören dem User, projektunabhängig.

Die Projekt-Zuweisung (+ tatsächliches Mounten) liegt in projects_mounts.py.
"""
from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._smbmount_helpers import (
    CreateMountRequest, UpdateMountRequest, mount_dict,
)
from hydrahive.credentials.store import get_credential
from hydrahive.smbmounts import db as mounts_db
from hydrahive.smbmounts.models import HOST_RE, NAME_RE, SHARE_RE, SUBPATH_RE

router = APIRouter(prefix="/api/smb-mounts", tags=["smb-mounts"])

_NAME = re.compile(NAME_RE)
_HOST = re.compile(HOST_RE)
_SHARE = re.compile(SHARE_RE)
_SUBPATH = re.compile(SUBPATH_RE)


def _mount_or_404(mount_id: str, username: str, role: str):
    m = mounts_db.get_mount(mount_id)
    if not m:
        raise coded(404, "mount_not_found")
    if role != "admin" and m.owner != username:
        raise coded(403, "mount_no_access")
    return m


def _validate_fields(name: str | None, host: str | None, share: str | None,
                     subpath: str | None, credential: str | None,
                     owner: str) -> None:
    if name is not None and not _NAME.match(name):
        raise coded(422, "mount_name_invalid")
    if host is not None and not _HOST.match(host):
        raise coded(422, "mount_host_invalid")
    if share is not None and not _SHARE.match(share):
        raise coded(422, "mount_share_invalid")
    if subpath:
        if not _SUBPATH.match(subpath) or ".." in subpath:
            raise coded(422, "mount_subpath_invalid")
    if credential:
        cred = get_credential(owner, credential)
        if cred is None or cred.type != "basic":
            raise coded(422, "mount_credential_invalid")


@router.get("")
def list_my_mounts(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    username, role = auth
    owner = None if role == "admin" else username
    return [mount_dict(m) for m in mounts_db.list_mounts(owner=owner)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_mount(
    req: CreateMountRequest,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    _validate_fields(req.name, req.host, req.share, req.subpath,
                     req.credential, username)
    if mounts_db.name_taken(username, req.name):
        raise coded(409, "mount_name_taken")
    m = mounts_db.create_mount(
        owner=username, name=req.name, host=req.host, share=req.share,
        subpath=req.subpath, credential=req.credential,
        read_only=req.read_only, options=req.options,
    )
    return mount_dict(m)


@router.get("/{mount_id}")
def get_one(
    mount_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    m = _mount_or_404(mount_id, *auth)
    return mount_dict(m)


@router.patch("/{mount_id}")
def update_one(
    mount_id: str,
    req: UpdateMountRequest,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, role = auth
    m = _mount_or_404(mount_id, username, role)
    if m.mount_state == "mounted":
        raise coded(409, "mount_is_mounted")
    _validate_fields(None, req.host, req.share, req.subpath,
                     req.credential, m.owner)
    mounts_db.update_mount(
        mount_id, host=req.host, share=req.share, subpath=req.subpath,
        credential=req.credential, read_only=req.read_only, options=req.options,
    )
    return mount_dict(mounts_db.get_mount(mount_id))


@router.delete("/{mount_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_one(
    mount_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    username, role = auth
    m = _mount_or_404(mount_id, username, role)
    if m.mount_state == "mounted":
        raise coded(409, "mount_is_mounted")
    mounts_db.delete_mount(mount_id)
