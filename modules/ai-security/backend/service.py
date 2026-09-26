"""Persistenz, Eigentümerprüfung und Report-Redaction."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from hydrahive.db.connection import db

VALID_STATUSES = {"queued", "running", "completed", "failed"}
_SENSITIVE_PARTS = ("token", "api_key", "apikey", "authorization", "password", "secret")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if any(part in key.lower() for part in _SENSITIVE_PARTS)
            else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def encode_result(value: Any, max_bytes: int) -> str:
    redacted = _redact(value)
    encoded = json.dumps(redacted, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > max_bytes:
        encoded = json.dumps(
            {"truncated": True, "reason": "result_too_large"},
            separators=(",", ":"),
        )
    return encoded


def _row(row: Any) -> dict[str, Any]:
    result = dict(row)
    if result.get("result_json"):
        try:
            result["result"] = json.loads(result.pop("result_json"))
        except (TypeError, ValueError):
            result["result"] = {"truncated": True, "reason": "invalid_stored_result"}
    else:
        result.pop("result_json", None)
        result["result"] = None
    return result


def create_scan(username: str, target_url: str) -> dict[str, Any]:
    scan_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            "INSERT INTO module_ai_security_scans (id, username, scan_type, target_url) "
            "VALUES (?, ?, 'infra', ?)",
            (scan_id, username, target_url),
        )
    return get_scan(username, scan_id)  # type: ignore[return-value]


def list_scans(username: str, limit: int = 50) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM module_ai_security_scans WHERE username = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (username, limit),
        ).fetchall()
    return [_row(row) for row in rows]


def list_active(limit: int = 20) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM module_ai_security_scans "
            "WHERE status IN ('queued', 'running') ORDER BY updated_at ASC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_scan(username: str, scan_id: str) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM module_ai_security_scans WHERE id = ? AND username = ?",
            (scan_id, username),
        ).fetchone()
    return _row(row) if row else None


def update_session(scan_id: str, session_id: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE module_ai_security_scans SET upstream_session_id = ?, status = 'running', "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (session_id, scan_id),
        )


def mark_failed(scan_id: str, error_code: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE module_ai_security_scans SET status = 'failed', error_code = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), "
            "completed_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (error_code[:80], scan_id),
        )


def mark_completed(scan_id: str, result: Any, max_bytes: int) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE module_ai_security_scans SET status = 'completed', result_json = ?, "
            "error_code = NULL, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), "
            "completed_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (encode_result(result, max_bytes), scan_id),
        )


def touch_running(scan_id: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE module_ai_security_scans SET status = 'running', "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (scan_id,),
        )


def is_stale(row: dict[str, Any], max_age_seconds: int = 600) -> bool:
    created = row.get("created_at")
    if not isinstance(created, str):
        return True
    try:
        timestamp = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except ValueError:
        return True
    return (datetime.now(timezone.utc) - timestamp).total_seconds() > max_age_seconds
