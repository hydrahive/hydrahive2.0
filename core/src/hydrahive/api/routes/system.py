from __future__ import annotations

import platform
import sys
import time
from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.routes._system_checks import (
    check_db_writable,
    check_disk,
    check_llm_configured,
    check_workspace_dir,
    count_agents,
    count_projects,
)
from hydrahive.db.connection import db
from hydrahive.settings import settings

router = APIRouter(prefix="/api/system", tags=["system"])

_start_time: float = 0.0


def set_start_time() -> None:
    global _start_time
    _start_time = time.time()


@router.get("/info")
def info(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    db_path = settings.sessions_db
    db_size = db_path.stat().st_size if db_path.exists() else 0
    return {
        "version": "2.0.0",
        "started_at": _start_time,
        "uptime_seconds": max(0.0, time.time() - _start_time),
        "python": sys.version.split()[0],
        "platform": f"{platform.system()} {platform.release()}",
        "data_dir": str(settings.data_dir),
        "config_dir": str(settings.config_dir),
        "db_path": str(db_path),
        "db_size_bytes": db_size,
    }


@router.get("/stats")
def stats(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    with db() as conn:
        sessions_total = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        sessions_active = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE status = 'active'"
        ).fetchone()[0]
        messages_total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        compactions = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE role = 'compaction'"
        ).fetchone()[0]
        tool_calls = conn.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0]
        tool_calls_ok = conn.execute(
            "SELECT COUNT(*) FROM tool_calls WHERE status = 'success'"
        ).fetchone()[0]
        tool_calls_err = conn.execute(
            "SELECT COUNT(*) FROM tool_calls WHERE status = 'error'"
        ).fetchone()[0]

    agents_count, agents_by_type = count_agents()
    projects_count, projects_active = count_projects()

    return {
        "agents": {"total": agents_count, "by_type": agents_by_type},
        "projects": {"total": projects_count, "active": projects_active},
        "sessions": {"total": sessions_total, "active": sessions_active},
        "messages": {"total": messages_total, "compactions": compactions},
        "tool_calls": {
            "total": tool_calls,
            "success": tool_calls_ok,
            "error": tool_calls_err,
            "success_rate": round(tool_calls_ok / tool_calls * 100, 1) if tool_calls else 0,
        },
    }


@router.get("/health")
def health(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    return {
        "checks": [
            check_db_writable(),
            check_llm_configured(),
            check_workspace_dir(),
            check_disk(),
        ],
    }
