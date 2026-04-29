"""Helper-Funktionen für /api/system/* — Health-Checks und Counts."""
from __future__ import annotations

import json
import os
import shutil

from hydrahive.db.connection import db
from hydrahive.settings import settings


def count_agents() -> tuple[int, dict]:
    if not settings.agents_dir.exists():
        return 0, {}
    by_type: dict[str, int] = {}
    total = 0
    for d in settings.agents_dir.iterdir():
        cfg = d / "config.json"
        if not cfg.exists():
            continue
        try:
            data = json.loads(cfg.read_text())
            t = data.get("type", "?")
            by_type[t] = by_type.get(t, 0) + 1
            total += 1
        except json.JSONDecodeError:
            continue
    return total, by_type


def count_projects() -> tuple[int, int]:
    pdir = settings.data_dir / "projects"
    if not pdir.exists():
        return 0, 0
    total, active = 0, 0
    for d in pdir.iterdir():
        cfg = d / "config.json"
        if not cfg.exists():
            continue
        try:
            data = json.loads(cfg.read_text())
            total += 1
            if data.get("status", "active") == "active":
                active += 1
        except json.JSONDecodeError:
            continue
    return total, active


def check_db_writable() -> dict:
    try:
        with db() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"name_code": "db", "ok": True, "detail_code": "db_ok"}
    except Exception as e:
        return {"name_code": "db", "ok": False, "detail": str(e)}


def check_llm_configured() -> dict:
    try:
        if not settings.llm_config.exists():
            return {"name_code": "llm", "ok": False, "detail_code": "llm_no_config"}
        cfg = json.loads(settings.llm_config.read_text())
        if not cfg.get("default_model"):
            return {"name_code": "llm", "ok": False, "detail_code": "llm_no_model"}
        providers = cfg.get("providers", [])
        if not providers:
            return {"name_code": "llm", "ok": False, "detail_code": "llm_no_provider"}
        return {
            "name_code": "llm",
            "ok": True,
            "detail_code": "llm_ok",
            "params": {"model": cfg["default_model"], "count": len(providers)},
        }
    except Exception as e:
        return {"name_code": "llm", "ok": False, "detail": str(e)}


def check_workspace_dir() -> dict:
    ws = settings.data_dir / "workspaces"
    if not ws.exists():
        return {"name_code": "workspaces", "ok": False, "detail_code": "workspaces_missing"}
    return {"name_code": "workspaces", "ok": os.access(ws, os.W_OK), "detail": str(ws)}


def check_disk() -> dict:
    try:
        usage = shutil.disk_usage(settings.data_dir)
        free_gb = usage.free / 1024**3
        free_pct = usage.free / usage.total * 100
        return {
            "name_code": "disk",
            "ok": free_pct > 5,
            "detail_code": "disk_detail",
            "params": {"free_gb": f"{free_gb:.1f}", "free_pct": f"{free_pct:.0f}"},
        }
    except Exception as e:
        return {"name_code": "disk", "ok": False, "detail": str(e)}
