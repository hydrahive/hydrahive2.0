"""Dashboard helpers: health check + stats query."""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone

from hydrahive.agentlink import is_connected as agentlink_connected
from hydrahive.settings import settings


def today_start_iso() -> str:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat()


def health_check() -> dict:
    backend = {"ok": True}
    agentlink = {"ok": agentlink_connected(), "configured": bool(settings.agentlink_url)}
    if not agentlink["configured"]:
        agentlink = {"ok": True, "configured": False}

    ip_bin = shutil.which("ip") or "/sbin/ip"
    bridge_ok = False
    try:
        r = subprocess.run([ip_bin, "-br", "link", "show", "br0"],
                           capture_output=True, text=True, timeout=2)
        bridge_ok = r.returncode == 0
    except Exception:
        pass

    ts_bin = shutil.which("tailscale")
    tailscale_ok = False
    tailscale_present = bool(ts_bin)
    if tailscale_present:
        try:
            r = subprocess.run([ts_bin, "status", "--json", "--peers=false"],
                               capture_output=True, text=True, timeout=2)
            tailscale_ok = r.returncode == 0 and '"BackendState":"Running"' in r.stdout
        except Exception:
            pass

    return {
        "backend": backend,
        "agentlink": agentlink,
        "bridge": {"ok": bridge_ok},
        "tailscale": {"ok": tailscale_ok, "configured": tailscale_present},
    }


def query_user_stats(conn, *, role: str, session_ids: list[str], today: str) -> tuple[int, int]:
    if role == "admin":
        tokens_today = conn.execute(
            "SELECT COALESCE(SUM(token_count), 0) FROM messages "
            "WHERE created_at >= ? AND role = 'assistant'", (today,),
        ).fetchone()[0]
        tool_calls_today = conn.execute(
            "SELECT COUNT(*) FROM tool_calls WHERE created_at >= ?", (today,),
        ).fetchone()[0]
    elif session_ids:
        placeholders = ",".join("?" * len(session_ids))
        tokens_today = conn.execute(
            f"SELECT COALESCE(SUM(token_count), 0) FROM messages "
            f"WHERE session_id IN ({placeholders}) AND created_at >= ? AND role = 'assistant'",
            [*session_ids, today],
        ).fetchone()[0]
        tool_calls_today = conn.execute(
            f"SELECT COUNT(*) FROM tool_calls m JOIN messages msg ON m.message_id = msg.id "
            f"WHERE msg.session_id IN ({placeholders}) AND m.created_at >= ?",
            [*session_ids, today],
        ).fetchone()[0]
    else:
        tokens_today = 0
        tool_calls_today = 0
    return tokens_today, tool_calls_today
