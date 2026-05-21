"""Nginx/Systemd-Logs → PostgreSQL-Mirror Import.

Liest access.log und journalctl-Output und schreibt HTTP-Requests
bzw. Service-Log-Einträge als Events in den Mirror.
ON CONFLICT DO NOTHING — idempotent.

event_type = "http_request"  → Nginx access.log
event_type = "service_log"   → journalctl -u hydrahive2
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_running: bool = False
_progress: dict = {"nginx": 0, "journal": 0}

# Nginx combined log format
_NGINX_RE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" '
    r'(?P<status>\d+) (?P<bytes>\d+)'
    r'(?:.+"(?P<referrer>[^"]*)" "(?P<ua>[^"]*)")?'
)
_NGINX_TIME_FMT = "%d/%b/%Y:%H:%M:%S %z"


def logs_import_status() -> dict:
    return {"running": _running, **_progress}


async def run_logs_import(
    nginx_log: str = "/var/log/nginx/access.log",
    journal_unit: str = "hydrahive2",
    journal_lines: int = 5000,
) -> None:
    global _running, _progress
    if _running:
        return
    _running = True
    _progress = {"nginx": 0, "journal": 0}
    try:
        from hydrahive.db import mirror
        if not mirror._pool:
            raise RuntimeError("PG-Mirror nicht aktiv")

        nginx_rows = await asyncio.to_thread(_parse_nginx, nginx_log)
        if nginx_rows:
            await _insert_rows(mirror._pool, nginx_rows)
            _progress["nginx"] = len(nginx_rows)

        journal_rows = await asyncio.to_thread(_parse_journal, journal_unit, journal_lines)
        if journal_rows:
            await _insert_rows(mirror._pool, journal_rows)
            _progress["journal"] = len(journal_rows)

        logger.info(
            "Log-Import: %d Nginx-Zeilen, %d Journal-Zeilen",
            _progress["nginx"], _progress["journal"],
        )
    except Exception as e:
        logger.warning("Log-Import fehlgeschlagen: %s", e)
    finally:
        _running = False


def _parse_nginx(log_path: str) -> list[dict]:
    path = Path(log_path)
    if not path.exists():
        logger.debug("Nginx-Log nicht gefunden: %s", log_path)
        return []

    rows = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            m = _NGINX_RE.match(line.strip())
            if not m:
                continue
            try:
                ts = datetime.strptime(m.group("time"), _NGINX_TIME_FMT)
            except ValueError:
                ts = datetime.now(timezone.utc)

            path_str = m.group("path") or "/"
            status = int(m.group("status") or 0)
            row_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"nginx:{m.group('ip')}:{m.group('time')}:{path_str}"))
            rows.append({
                "id": row_id,
                "event_type": "http_request",
                "text": f"{m.group('method')} {path_str} → {status}",
                "tool_name": str(status),
                "tool_input": json.dumps({
                    "ip": m.group("ip"), "method": m.group("method"),
                    "path": path_str, "status": status,
                    "bytes": int(m.group("bytes") or 0),
                    "ua": m.group("ua") or "",
                }),
                "created_at": ts,
            })
    return rows


def _parse_journal(unit: str, lines: int) -> list[dict]:
    try:
        result = subprocess.run(
            ["journalctl", "-u", unit, "-n", str(lines), "--no-pager", "-o", "short-iso"],
            capture_output=True, text=True, timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0:
        return []

    rows = []
    ts_re = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4})")
    for line in result.stdout.splitlines():
        m = ts_re.match(line)
        try:
            ts = datetime.fromisoformat(m.group(1)) if m else datetime.now(timezone.utc)
        except ValueError:
            ts = datetime.now(timezone.utc)

        text = line[len(m.group(0)):].strip() if m else line.strip()
        if not text:
            continue

        is_error = any(w in text.lower() for w in ("error", "exception", "traceback", "critical"))
        row_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"journal:{unit}:{line[:80]}"))
        rows.append({
            "id": row_id,
            "event_type": "service_log",
            "text": text[:500],
            "tool_name": unit,
            "tool_input": json.dumps({"unit": unit, "line": line[:500]}),
            "created_at": ts,
            "is_error": is_error,
        })
    return rows


async def _insert_rows(pool, rows: list[dict]) -> None:
    async with pool.acquire() as conn:
        await conn.executemany("""
            INSERT INTO events (id, message_id, session_id, block_index, chunk_index,
              chunk_total, username, agent_id, agent_name, project_id, event_type,
              text, tool_name, tool_use_id, tool_input, tool_output, is_error,
              token_count, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15::jsonb,$16,$17,$18,$19)
            ON CONFLICT (id) DO NOTHING
        """, [
            (r["id"], r["id"], "system-logs", 0, 0, 1,
             None, None, None, None,
             r["event_type"], r["text"], r.get("tool_name"), None,
             r.get("tool_input", "{}"), None, r.get("is_error", False),
             None, r["created_at"])
            for r in rows
        ])
