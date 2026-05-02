"""Disk-Image-Import: qcow2/raw/vmdk/vdi → qcow2 in vms_disks_dir.

Workflow:
1. Quelle (Upload-File ODER Pfad) wird in vms_imports_tmp/ bereitgelegt
2. `qemu-img info` erkennt Format
3. Wenn schon qcow2: copy/move. Sonst: `qemu-img convert -p -f <fmt> -O qcow2 src dst`
4. Progress wird aus stderr von qemu-img convert gelesen ('-p' liefert "(XX.XX/100%)")
5. Erfolg: Job-Status 'done', Disk liegt unter vms_disks_dir/<job_id>.qcow2
6. Fehler: Job-Status 'failed' mit error_code

Background-Tasks via asyncio.create_task — kein eigener Worker-Daemon.
"""
from __future__ import annotations

import asyncio
import logging
import re
import shutil
from pathlib import Path

from hydrahive.db._utils import now_iso
from hydrahive.settings import settings
from hydrahive.vms._import_job_db import db_create_job, db_delete, db_get, db_list, db_update

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {"qcow2", "raw", "vmdk", "vdi", "vhd", "vhdx", "vpc"}
PROGRESS_RE = re.compile(r"\(([\d.]+)/100%\)")

__all__ = [
    "db_create_job", "db_delete", "db_get", "db_list", "db_update",
    "detect_format", "run_convert", "execute_job", "ImportError_",
]


class ImportError_(RuntimeError):
    def __init__(self, code: str, **params):
        super().__init__(f"{code}: {params}")
        self.code = code
        self.params = params


def _imports_tmp() -> Path:
    return settings.vms_dir / "imports-tmp"


async def detect_format(src: Path) -> str:
    """`qemu-img info --output=json` parst Format. Wirft ImportError bei unsupported."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "qemu-img", "info", "--output=json", str(src),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        raise ImportError_("qemu_img_missing")
    out, err = await asyncio.wait_for(proc.communicate(), timeout=30.0)
    if proc.returncode != 0:
        raise ImportError_("import_format_unknown", stderr=err.decode(errors="replace")[:200])
    import json
    info = json.loads(out)
    fmt = info.get("format", "")
    if fmt not in SUPPORTED_FORMATS:
        raise ImportError_("import_format_unsupported", format=fmt)
    return fmt


async def run_convert(src: Path, dst: Path, src_format: str, job_id: str) -> None:
    """qemu-img convert mit Progress-Parsing aus stderr."""
    args = ["qemu-img", "convert", "-p", "-f", src_format, "-O", "qcow2",
            str(src), str(dst)]
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
    except FileNotFoundError:
        raise ImportError_("qemu_img_missing")
    assert proc.stdout is not None
    buf = b""
    while True:
        chunk = await proc.stdout.read(64)
        if not chunk:
            break
        buf += chunk
        # qemu-img progress kommt als " (XX.XX/100%)\r" — wir matchen unabhängig
        for m in PROGRESS_RE.finditer(buf.decode("ascii", "replace")):
            pct = int(float(m.group(1)))
            db_update(job_id, progress_pct=pct)
        if len(buf) > 4096:
            buf = buf[-1024:]
    rc = await proc.wait()
    if rc != 0:
        raise ImportError_("import_convert_failed", rc=rc)


async def execute_job(job_id: str, *, cleanup_source: bool = True) -> None:
    """Hintergrund-Task: macht detect_format → convert → DB-Update."""
    job = db_get(job_id)
    if not job:
        return
    src = Path(job["source_path"])
    dst = Path(job["target_qcow2"])
    db_update(job_id, status="running")
    try:
        if not src.exists():
            raise ImportError_("import_source_missing")
        fmt = await detect_format(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        await run_convert(src, dst, fmt, job_id)
        db_update(job_id, status="done", progress_pct=100, finished_at=now_iso())
    except ImportError_ as e:
        logger.warning("Import-Job %s fehlgeschlagen: %s", job_id, e.code)
        db_update(job_id, status="failed", error_code=e.code, finished_at=now_iso())
        dst.unlink(missing_ok=True)
    except Exception as e:
        logger.exception("Import-Job %s unerwarteter Fehler", job_id)
        db_update(job_id, status="failed", error_code="import_internal_error",
                  finished_at=now_iso())
        dst.unlink(missing_ok=True)
    finally:
        if cleanup_source:
            src.unlink(missing_ok=True)
