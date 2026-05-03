"""Datamining DB Export / Import — pg_dump / pg_restore über die API."""
from __future__ import annotations

import asyncio
import logging
import shutil
import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from hydrahive.api.middleware.auth import require_admin
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/datamining", tags=["datamining"])

_EXPORTS_DIR = settings.data_dir / "exports"

_export_state: dict = {"running": False, "done": False, "file": None, "size_mb": 0, "error": None}
_import_state: dict = {"running": False, "done": False, "error": None}


def _dsn() -> str:
    dsn = settings.pg_mirror_dsn
    if not dsn:
        raise HTTPException(503, "pg_mirror_dsn nicht konfiguriert")
    return dsn


@router.post("/export", dependencies=[Depends(require_admin)])
async def start_export() -> dict:
    if _export_state["running"]:
        return {"ok": False, "reason": "Export läuft bereits"}
    _EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dsn = _dsn()
    asyncio.get_running_loop().create_task(_run_export(dsn))
    return {"ok": True}


@router.get("/export/status", dependencies=[Depends(require_admin)])
def export_status() -> dict:
    s = dict(_export_state)
    if s["file"] and Path(s["file"]).exists():
        s["filename"] = Path(s["file"]).name
    else:
        s["filename"] = None
    return s


@router.get("/export/download", dependencies=[Depends(require_admin)])
def export_download() -> FileResponse:
    f = _export_state.get("file")
    if not f or not Path(f).exists():
        raise HTTPException(404, "Kein Export vorhanden")
    return FileResponse(
        path=f,
        filename=Path(f).name,
        media_type="application/octet-stream",
    )


@router.post("/import", dependencies=[Depends(require_admin)])
async def start_import(file: UploadFile) -> dict:
    if _import_state["running"]:
        return {"ok": False, "reason": "Import läuft bereits"}
    _EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = _EXPORTS_DIR / f"import_{int(time.time())}.dump"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    dsn = _dsn()
    asyncio.get_running_loop().create_task(_run_import(dsn, dest))
    return {"ok": True}


@router.get("/import/status", dependencies=[Depends(require_admin)])
def import_status() -> dict:
    return dict(_import_state)


async def _run_export(dsn: str) -> None:
    _export_state.update(running=True, done=False, file=None, size_mb=0, error=None)
    ts = int(time.time())
    out = _EXPORTS_DIR / f"datamining_{ts}.dump"
    try:
        proc = await asyncio.create_subprocess_exec(
            "pg_dump", "--format=custom", "--compress=9", f"--file={out}", dsn,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode())
        size_mb = round(out.stat().st_size / 1024 / 1024, 1)
        _export_state.update(running=False, done=True, file=str(out), size_mb=size_mb)
        logger.info("DB-Export fertig: %s (%.1f MB)", out.name, size_mb)
        _cleanup_old_exports(keep=str(out))
    except Exception as e:
        _export_state.update(running=False, done=False, error=str(e))
        logger.warning("DB-Export fehlgeschlagen: %s", e)
        if out.exists():
            out.unlink()


async def _run_import(dsn: str, dump_file: Path) -> None:
    _import_state.update(running=True, done=False, error=None)
    try:
        proc = await asyncio.create_subprocess_exec(
            "pg_restore", "--clean", "--if-exists", f"--dbname={dsn}", str(dump_file),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode not in (0, 1):  # 1 = warnings, nicht fatal
            raise RuntimeError(stderr.decode())
        _import_state.update(running=False, done=True)
        logger.info("DB-Import abgeschlossen: %s", dump_file.name)
    except Exception as e:
        _import_state.update(running=False, done=False, error=str(e))
        logger.warning("DB-Import fehlgeschlagen: %s", e)
    finally:
        if dump_file.exists():
            dump_file.unlink()


def _cleanup_old_exports(keep: str) -> None:
    for f in _EXPORTS_DIR.glob("datamining_*.dump"):
        if str(f) != keep:
            f.unlink(missing_ok=True)
