"""Neustart darf nicht an offenen SSE-Verbindungen hängen (Task 06d38ae9).

uvicorn wartet ohne --timeout-graceful-shutdown unbegrenzt auf offene Verbindungen
(/api/agents/activity/stream ist in jedem Browser-Tab offen). systemd killt nach 90 s
mit SIGKILL, der lifespan-Shutdown (u. a. wa_bridge.stop()) läuft nie.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "installer"
SYSTEMD = (INSTALLER / "modules" / "50-systemd.sh").read_text(encoding="utf-8")
UPDATE = (INSTALLER / "update.sh").read_text(encoding="utf-8")
LAUNCHD = (INSTALLER / "modules-mac" / "50-launchd.sh").read_text(encoding="utf-8")
UPDATE_MAC = (INSTALLER / "update-mac.sh").read_text(encoding="utf-8")

OPT = "--timeout-graceful-shutdown"


def _seconds(text: str) -> int:
    m = re.search(OPT + r"(?:\s+|</string>\s*<string>)(\d+)", text)
    assert m, f"{OPT} fehlt"
    return int(m.group(1))


def _timeout_stop_sec(unit: str) -> int:
    m = re.search(r"^TimeoutStopSec=(\d+)", unit, re.M)
    return int(m.group(1)) if m else 90          # systemd-Standard


def test_systemd_unit_limits_graceful_shutdown_below_stop_timeout() -> None:
    exec_start = next(line for line in SYSTEMD.splitlines() if line.startswith("ExecStart=") and "uvicorn" in line)
    secs = _seconds(exec_start)
    assert 5 <= secs <= _timeout_stop_sec(SYSTEMD) - 30       # Luft für den lifespan-Shutdown


def test_update_rewrites_unit_without_graceful_timeout() -> None:
    assert f'grep -q -- "{OPT}" "$SERVICE_FILE" || NEEDS_REWRITE=1' in UPDATE


def test_launchd_plist_limits_graceful_shutdown() -> None:
    assert 5 <= _seconds(LAUNCHD) <= 60


def test_update_mac_rewrites_plist_without_graceful_timeout() -> None:
    assert f'grep -q -- "{OPT}" "$BACKEND_PLIST"' in UPDATE_MAC
