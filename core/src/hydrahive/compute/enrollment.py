"""Opaque, one-time enrollment tokens for compute nodes."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from hydrahive.compute import audit
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db
from hydrahive.settings import settings

MIN_TTL_SECONDS = 30
MAX_TTL_SECONDS = 3600
MAX_TOKEN_LENGTH = 128
MAX_NAME_LENGTH = 128
MAX_ACTOR_LENGTH = 128
TOKEN_RETENTION_DAYS = 7


class EnrollmentError(RuntimeError):
    def __init__(self) -> None:
        self.code = "enrollment_invalid"
        super().__init__(self.code)


@dataclass(frozen=True)
class CreatedEnrollmentToken:
    token_id: str
    token: str
    requested_name: str
    expires_at: str


@dataclass(frozen=True)
class ConsumedEnrollmentToken:
    token_id: str
    requested_name: str
    created_by: str


def _validate_text(value: str, field: str, maximum: int) -> str:
    value = value.strip()
    if not value or len(value) > maximum or not value.isprintable():
        raise ValueError(f"{field} must contain 1-{maximum} printable characters")
    return value


def validate_token(token: str) -> str:
    if not isinstance(token, str) or not 32 <= len(token) <= MAX_TOKEN_LENGTH or not token.isascii():
        raise EnrollmentError()
    return token


def token_digest(token: str) -> str:
    validate_token(token)
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        b"hydrahive-compute-enrollment-v1\0" + token.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def create_token(
    *,
    requested_name: str,
    created_by: str,
    ttl_seconds: int = 900,
) -> CreatedEnrollmentToken:
    requested_name = _validate_text(requested_name, "requested_name", MAX_NAME_LENGTH)
    created_by = _validate_text(created_by, "created_by", MAX_ACTOR_LENGTH)
    if not MIN_TTL_SECONDS <= ttl_seconds <= MAX_TTL_SECONDS:
        raise ValueError(f"ttl_seconds must be between {MIN_TTL_SECONDS} and {MAX_TTL_SECONDS}")

    token = secrets.token_urlsafe(32)
    token_id = uuid7()
    expires_at = (datetime.now(UTC) + timedelta(seconds=ttl_seconds)).isoformat().replace("+00:00", "Z")
    with db() as conn:
        retention_cutoff = (datetime.now(UTC) - timedelta(days=TOKEN_RETENTION_DAYS)).isoformat().replace("+00:00", "Z")
        conn.execute(
            """DELETE FROM compute_enrollment_results
               WHERE token_id IN (
                   SELECT token_id FROM compute_enrollment_tokens
                   WHERE expires_at < ? AND (consumed_at IS NULL OR consumed_at < ?)
               )""",
            (retention_cutoff, retention_cutoff),
        )
        conn.execute(
            """DELETE FROM compute_enrollment_tokens
               WHERE expires_at < ? AND (consumed_at IS NULL OR consumed_at < ?)""",
            (retention_cutoff, retention_cutoff),
        )
        conn.execute(
            """INSERT INTO compute_enrollment_tokens
                   (token_id, token_hmac, requested_name, expires_at, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (token_id, token_digest(token), requested_name, expires_at, created_by, now_iso()),
        )
        audit.record_in_connection(
            conn,
            actor=created_by,
            action="enrollment.created",
            details={"token_id": token_id, "requested_name": requested_name},
        )
    return CreatedEnrollmentToken(token_id, token, requested_name, expires_at)


def consume_token(token: str) -> ConsumedEnrollmentToken:
    digest = token_digest(token)
    consumed_at = now_iso()
    with db(immediate=True) as conn:
        row = conn.execute(
            """SELECT token_id, requested_name, created_by
               FROM compute_enrollment_tokens
               WHERE token_hmac = ? AND consumed_at IS NULL AND expires_at > ?""",
            (digest, consumed_at),
        ).fetchone()
        if row is None:
            raise EnrollmentError()
        result = conn.execute(
            """UPDATE compute_enrollment_tokens SET consumed_at = ?
               WHERE token_id = ? AND consumed_at IS NULL AND expires_at > ?""",
            (consumed_at, row["token_id"], consumed_at),
        )
        if result.rowcount != 1:  # pragma: no cover - BEGIN IMMEDIATE serializes consumers
            raise EnrollmentError()
    return ConsumedEnrollmentToken(row["token_id"], row["requested_name"], row["created_by"])
