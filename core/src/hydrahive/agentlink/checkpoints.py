"""Versioned, bounded checkpoint metadata transported in AgentLink findings."""
from __future__ import annotations

import json
import re

CHECKPOINT_PREFIX = "HH_CHECKPOINT_V1:"
_CHECKPOINT_VERSION = 1
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def checkpoint_finding(
    *, resume_token: str, session_id: str, remaining_work: str,
    reason: str = "max_iterations",
) -> str:
    """`reason` dokumentiert, warum pausiert wurde (Budget erreicht, Server-Shutdown, ...).
    Spec delegation-reliability.md 3.2: neben `max_iterations` jetzt auch `shutdown`
    (Auftrag bekommt beim geplanten Server-Stopp eine Chance zum Fortsetzen statt
    unwiderruflich auf `lost` zu fallen)."""
    if not _TOKEN.fullmatch(resume_token):
        raise ValueError("Ungültiges Resume-Token")
    if not _SESSION_ID.fullmatch(session_id):
        raise ValueError("Ungültige Session-ID")
    payload = {
        "version": _CHECKPOINT_VERSION,
        "reason": reason,
        "resume_token": resume_token,
        "session_id": session_id,
        "remaining_work": remaining_work[:500],
    }
    return CHECKPOINT_PREFIX + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def split_checkpoint_findings(findings: list[str]) -> tuple[list[str], dict | None]:
    """Separate one valid checkpoint marker from human-readable partial findings."""
    visible: list[str] = []
    checkpoint: dict | None = None
    for finding in findings:
        if not isinstance(finding, str) or not finding.startswith(CHECKPOINT_PREFIX):
            if isinstance(finding, str) and finding:
                visible.append(finding)
            continue
        if checkpoint is not None or len(finding) > 2_048:
            continue
        try:
            payload = json.loads(finding.removeprefix(CHECKPOINT_PREFIX))
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        token = payload.get("resume_token")
        session_id = payload.get("session_id")
        remaining = payload.get("remaining_work")
        reason = payload.get("reason")
        if (
            payload.get("version") != _CHECKPOINT_VERSION
            or not isinstance(reason, str) or not reason
            or not isinstance(token, str) or not _TOKEN.fullmatch(token)
            or not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id)
            or not isinstance(remaining, str) or len(remaining) > 500
        ):
            continue
        checkpoint = {
            "version": _CHECKPOINT_VERSION,
            "reason": reason,
            "resume_token": token,
            "session_id": session_id,
            "remaining_work": remaining,
        }
    return visible, checkpoint
