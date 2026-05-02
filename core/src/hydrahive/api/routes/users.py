from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import FileResponse

from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel

from hydrahive.agents import bootstrap as agent_bootstrap, config as agent_config
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.users import (
    create,
    delete,
    list_users,
    update_password,
    update_role,
)
from hydrahive.backup.user_archive import create_user_archive
from hydrahive.backup.user_restore import UserRestoreError, restore_user_archive

router = APIRouter(prefix="/api/users", tags=["users"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class ChangePasswordRequest(BaseModel):
    new_password: str


class UpdateUserRequest(BaseModel):
    role: str | None = None


@router.get("", dependencies=[Depends(require_admin)])
def get_users() -> list[dict]:
    return list_users()


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_user(req: CreateUserRequest) -> dict:
    try:
        create(req.username, req.password, req.role)
    except ValueError:
        raise coded(status.HTTP_409_CONFLICT, "username_exists")
    agent_bootstrap.ensure_master(req.username)
    return {"username": req.username, "role": req.role}


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_user(username: str) -> None:
    for agent in agent_config.list_by_owner(username):
        agent_config.delete(agent["id"])
    delete(username)


@router.patch("/{username}", dependencies=[Depends(require_admin)])
def update_user(username: str, req: UpdateUserRequest) -> dict:
    if req.role is not None:
        try:
            update_role(username, req.role)
        except ValueError as e:
            msg = str(e)
            if msg == "last_admin":
                raise coded(status.HTTP_400_BAD_REQUEST, "last_admin_cannot_demote")
            if msg.startswith("Ungültige Rolle"):
                raise coded(status.HTTP_400_BAD_REQUEST, "invalid_role", role=req.role)
            raise coded(status.HTTP_404_NOT_FOUND, "user_not_found")
    return {"ok": True}


@router.patch("/me/password")
def change_own_password(
    req: ChangePasswordRequest,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    try:
        update_password(username, req.new_password)
    except ValueError:
        raise coded(status.HTTP_404_NOT_FOUND, "user_not_found")
    return {"ok": True}


@router.post("/me/backup")
def backup_own_data(
    background: BackgroundTasks,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> FileResponse:
    username, _ = auth
    tmp_dir = Path(tempfile.mkdtemp(prefix="hh2-user-backup-"))
    try:
        archive = create_user_archive(username, tmp_dir)
    except OSError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "backup_create_failed",
                    error=str(e))
    background.add_task(shutil.rmtree, tmp_dir, ignore_errors=True)
    return FileResponse(path=archive, filename=archive.name, media_type="application/gzip")


@router.post("/me/restore")
async def restore_own_data(
    archive: Annotated[UploadFile, File()],
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    if not archive.filename:
        raise coded(status.HTTP_400_BAD_REQUEST, "backup_filename_missing")

    tmp_dir = Path(tempfile.mkdtemp(prefix="hh2-user-restore-"))
    upload_path = tmp_dir / "upload.tar.gz"
    try:
        with upload_path.open("wb") as f:
            while True:
                chunk = await archive.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        try:
            restore_user_archive(upload_path, username)
        except UserRestoreError as e:
            raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
        except OSError as e:
            raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "backup_restore_failed",
                        error=str(e))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return {"restored": True}


@router.patch("/{username}/password", dependencies=[Depends(require_admin)])
def change_password(username: str, req: ChangePasswordRequest) -> dict:
    try:
        update_password(username, req.new_password)
    except ValueError:
        raise coded(status.HTTP_404_NOT_FOUND, "user_not_found")
    return {"ok": True}
