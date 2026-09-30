"""Dashboard helpers: health check + stats query."""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from hydrahive.agentlink import is_connected as agentlink_connected
from hydrahive.api.routes._websearch_health import websearch_health
from hydrahive.settings import settings


# „Heute“ im Dashboard = deutscher Kalendertag (Till, 30.09.2026, Task a1b95d3b).
_DAY_TZ = ZoneInfo("Europe/Berlin")


def _local_midnight(now: datetime | None, days_back: int = 0) -> str:
    """Deutsche Mitternacht (heute minus days_back) als UTC-Text …+00:00.

    Die DB speichert UTC; im selben Textformat ist die Grenze direkt mit
    created_at vergleichbar (auch mit alten …Z-Zeitstempeln)."""
    local = (now or datetime.now(timezone.utc)).astimezone(_DAY_TZ)
    day = local.date() - timedelta(days=days_back)
    start = datetime(day.year, day.month, day.day, tzinfo=_DAY_TZ)
    return start.astimezone(timezone.utc).isoformat()


def today_start_iso(now: datetime | None = None) -> str:
    return _local_midnight(now)


def week_start_iso(now: datetime | None = None) -> str:
    """Beginn der letzten 7 deutschen Kalendertage (heute eingeschlossen: 7 volle Tage zurück)."""
    return _local_midnight(now, days_back=7)


def health_check() -> dict:
    backend = {"ok": True}
    # AgentLink gehört zur Grundinstallation. Ein Ausfall wird darum als nicht-ok
    # gemeldet — vorher galt "nicht konfiguriert" als ok=True, wodurch ein
    # fehlgeschlagenes Setup unsichtbar blieb und ask_agent still verschwand.
    # Nur eine ausdrückliche Abschaltung (HH_AGENTLINK_URL="") bleibt unkritisch.
    configured = bool(settings.agentlink_url)
    agentlink = {
        "ok": agentlink_connected() if configured else True,
        "configured": configured,
        "required": True,
    }

    ip_bin = shutil.which("ip") or "/sbin/ip"
    bridge_ok = False
    try:
        r = subprocess.run([ip_bin, "-br", "link", "show", "br0"],
                           capture_output=True, text=True, timeout=2)
        bridge_ok = r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        pass

    ts_bin = shutil.which("tailscale")
    tailscale_ok = False
    tailscale_present = bool(ts_bin)
    if tailscale_present:
        try:
            r = subprocess.run([ts_bin, "status", "--json", "--peers=false"],
                               capture_output=True, text=True, timeout=2)
            tailscale_ok = r.returncode == 0 and '"BackendState":"Running"' in r.stdout
        except (OSError, subprocess.SubprocessError):
            pass

    return {
        "backend": backend,
        "agentlink": agentlink,
        "bridge": {"ok": bridge_ok},
        "tailscale": {"ok": tailscale_ok, "configured": tailscale_present},
        "websearch": websearch_health(),
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
