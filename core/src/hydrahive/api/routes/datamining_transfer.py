"""Datamining DB Export / Import — pg_dump / pg_restore über die API."""
from __future__ import annotations

import asyncio
import logging
import re
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
_merge_import_state: dict = {"running": False, "done": False, "error": None}


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


@router.post("/import-merge", dependencies=[Depends(require_admin)])
async def start_import_merge(file: UploadFile) -> dict:
    if _merge_import_state["running"]:
        return {"ok": False, "reason": "Merge-Import läuft bereits"}
    _EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = _EXPORTS_DIR / f"merge_import_{int(time.time())}.dump"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    dsn = _dsn()
    asyncio.get_running_loop().create_task(_run_import_merge(dsn, dest))
    return {"ok": True}


@router.get("/import-merge/status", dependencies=[Depends(require_admin)])
def import_merge_status() -> dict:
    return dict(_merge_import_state)


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


_COPY_RE = re.compile(r"COPY (\S+) \(([^)]+)\) FROM stdin;")


def _copy_via_temp_table(src: Path, dst: Path, target_cols: dict[str, set[str]] | None = None) -> None:
    """Wandelt COPY-Blöcke in Temp-Table-Routing um: COPY → temp → INSERT ON CONFLICT DO NOTHING.

    Behält das native COPY-Format (schnell, kein Quoting nötig).
    Filtert Quellspalten auf tatsächlich existierende Zielspalten.

    Pro Tabelle wird erzeugt:
        BEGIN;
        CREATE TEMP TABLE _mg_<tbl> AS SELECT <cols> FROM <tbl> LIMIT 0;
        COPY _mg_<tbl> (<cols>) FROM stdin;
        <Daten, ggf. Spalten gefiltert>
        \\.
        INSERT INTO <tbl> (<cols>) SELECT <cols> FROM _mg_<tbl> ON CONFLICT DO NOTHING;
        DROP TABLE _mg_<tbl>;
        COMMIT;
    """
    in_copy = False
    table_expr = ""
    tbl_name = ""
    cols_str = ""
    col_indices: list[int] | None = None

    with src.open("r", encoding="utf-8", errors="replace") as fin, \
         dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            stripped = line.rstrip("\n")
            if not in_copy:
                m = _COPY_RE.match(stripped)
                if m:
                    table_expr = m.group(1)
                    src_cols = [c.strip() for c in m.group(2).split(",")]
                    tbl_name = table_expr.split(".")[-1]
                    if target_cols and tbl_name in target_cols:
                        tgt = target_cols[tbl_name]
                        keep = [(i, c) for i, c in enumerate(src_cols) if c in tgt]
                        col_indices = [i for i, _ in keep]
                        cols_str = ", ".join(c for _, c in keep)
                        logger.info("Merge %s: %d/%d Spalten", tbl_name, len(keep), len(src_cols))
                    else:
                        col_indices = None
                        cols_str = ", ".join(src_cols)
                    tmp = f"_mg_{tbl_name}"
                    fout.write("BEGIN;\n")
                    fout.write(f"CREATE TEMP TABLE {tmp} AS SELECT {cols_str} FROM {table_expr} LIMIT 0;\n")
                    fout.write(f"COPY {tmp} ({cols_str}) FROM stdin;\n")
                    in_copy = True
                elif not stripped.startswith("\\"):
                    fout.write(line)
            elif stripped == "\\.":
                in_copy = False
                tmp = f"_mg_{tbl_name}"
                fout.write("\\.\n")
                fout.write(f"INSERT INTO {table_expr} ({cols_str})\n")
                fout.write(f"  SELECT {cols_str} FROM {tmp} ON CONFLICT DO NOTHING;\n")
                fout.write(f"DROP TABLE {tmp};\n")
                fout.write("COMMIT;\n")
                col_indices = None
            else:
                if col_indices is not None:
                    fields = stripped.split("\t")
                    fout.write("\t".join(
                        fields[i] if i < len(fields) else "\\N" for i in col_indices
                    ) + "\n")
                else:
                    fout.write(line)


async def _query_target_cols(dsn: str) -> dict[str, set[str]]:
    """Fragt die tatsächlich vorhandenen Spalten aller Datamining-Tabellen ab."""
    try:
        import asyncpg  # noqa: PLC0415
        conn = await asyncpg.connect(dsn, command_timeout=10)
        try:
            result: dict[str, set[str]] = {}
            for tbl in ("sessions", "events", "llm_calls", "compaction_events", "errors_log"):
                rows = await conn.fetch(
                    "SELECT attname FROM pg_attribute "
                    "WHERE attrelid = $1::regclass AND attnum > 0 AND NOT attisdropped",
                    tbl,
                )
                result[tbl] = {r["attname"] for r in rows}
            return result
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("DB-Merge: Zielspalten-Abfrage fehlgeschlagen: %s", e)
        return {}


async def _run_import_merge(dsn: str, dump_file: Path) -> None:
    _merge_import_state.update(running=True, done=False, error=None)
    ts = int(time.time())
    sql_raw = _EXPORTS_DIR / f"merge_{ts}_raw.sql"
    sql_patched = _EXPORTS_DIR / f"merge_{ts}.sql"

    try:
        # Zielspalten abfragen — Quellspalten die nicht existieren (z.B. embedding) werden gefiltert
        target_cols = await _query_target_cols(dsn)
        logger.info("DB-Merge Zielspalten: %s", {t: len(c) for t, c in target_cols.items()})

        # pg_restore --data-only → COPY-SQL (ohne DB-Verbindung, --file= nötig)
        p = await asyncio.create_subprocess_exec(
            "pg_restore", "--data-only", "--no-privileges", f"--file={sql_raw}", str(dump_file),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, err = await p.communicate()
        pg_restore_stderr = err.decode().strip()
        raw_size = sql_raw.stat().st_size if sql_raw.exists() else 0
        logger.info("DB-Merge pg_restore: rc=%d, raw_sql=%d bytes, stderr=%s",
                    p.returncode, raw_size, pg_restore_stderr[:200] or "(leer)")
        if p.returncode not in (0, 1):
            raise RuntimeError(pg_restore_stderr)

        # COPY-Blöcke → Temp-Table-Routing (COPY bleibt COPY, kein INSERT-pro-Row)
        await asyncio.get_running_loop().run_in_executor(
            None, _copy_via_temp_table, sql_raw, sql_patched, target_cols
        )
        patched_size = sql_patched.stat().st_size if sql_patched.exists() else 0
        logger.info("DB-Merge COPY→INSERT: patched_sql=%d bytes", patched_size)

        # Zeilen vor dem Import zählen
        import asyncpg as _asyncpg  # noqa: PLC0415
        _conn = await _asyncpg.connect(dsn, command_timeout=30)
        try:
            before = {t: await _conn.fetchval(f"SELECT COUNT(*)::int FROM {t}")
                      for t in ("sessions", "events", "llm_calls", "compaction_events", "errors_log")}
        finally:
            await _conn.close()
        logger.info("DB-Merge vor Import: %s", before)

        with sql_patched.open("rb") as fh:
            p = await asyncio.create_subprocess_exec(
                # ON_ERROR_STOP=1: bei echtem Fehler sofort abbrechen und rc!=0 liefern
                "psql", "--set=ON_ERROR_STOP=1", dsn,
                stdin=fh, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            _, err = await p.communicate()
            psql_stderr = err.decode().strip()
            logger.info("DB-Merge psql: rc=%d, stderr=%s", p.returncode, psql_stderr[:2000] or "(leer)")
            if p.returncode != 0:
                raise RuntimeError(psql_stderr[:1000])

        # Zeilen nach dem Import zählen
        _conn = await _asyncpg.connect(dsn, command_timeout=30)
        try:
            after = {t: await _conn.fetchval(f"SELECT COUNT(*)::int FROM {t}")
                     for t in ("sessions", "events", "llm_calls", "compaction_events", "errors_log")}
        finally:
            await _conn.close()
        inserted = {t: after[t] - before.get(t, 0) for t in after}
        logger.info("DB-Merge nach Import: %s | neu: %s", after, inserted)

        _merge_import_state.update(running=False, done=True)
        logger.info("DB-Merge-Import abgeschlossen: %s", dump_file.name)
    except Exception as e:
        _merge_import_state.update(running=False, done=False, error=str(e))
        logger.warning("DB-Merge-Import fehlgeschlagen: %s", e)
    finally:
        sql_raw.unlink(missing_ok=True)
        sql_patched.unlink(missing_ok=True)
        if dump_file.exists():
            dump_file.unlink()
