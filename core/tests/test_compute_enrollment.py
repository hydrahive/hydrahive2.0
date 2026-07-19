from __future__ import annotations

import base64
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from hydrahive.compute import enrollment
from hydrahive.db.connection import init_db
from hydrahive.settings import settings


@pytest.fixture
def enrollment_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    database = tmp_path / "enrollment.db"
    monkeypatch.setattr(settings, "sessions_db", database, raising=False)
    monkeypatch.setattr(settings, "secret_key", "test-secret-with-more-than-thirty-two-bytes", raising=False)
    init_db()
    return database


def _decode_token(token: str) -> bytes:
    return base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))


def test_enrollment_token_has_256_bits_and_only_hmac_is_stored(enrollment_db: Path) -> None:
    created = enrollment.create_token(requested_name="Node A", created_by="admin", ttl_seconds=600)

    assert len(_decode_token(created.token)) == 32
    with sqlite3.connect(enrollment_db) as conn:
        row = conn.execute(
            "SELECT token_hmac, requested_name, consumed_at FROM compute_enrollment_tokens WHERE token_id = ?",
            (created.token_id,),
        ).fetchone()
    assert row is not None
    assert row[0] != created.token
    assert len(row[0]) == 64
    assert row[1:] == ("Node A", None)


def test_enrollment_token_is_consumed_exactly_once(enrollment_db: Path) -> None:
    created = enrollment.create_token(requested_name="Node A", created_by="admin", ttl_seconds=600)

    consumed = enrollment.consume_token(created.token)
    assert consumed.token_id == created.token_id
    assert consumed.requested_name == "Node A"

    with pytest.raises(enrollment.EnrollmentError) as reused:
        enrollment.consume_token(created.token)
    assert reused.value.code == "enrollment_invalid"


def test_wrong_and_expired_tokens_return_same_generic_error(enrollment_db: Path) -> None:
    created = enrollment.create_token(requested_name="Node A", created_by="admin", ttl_seconds=60)
    expired_at = (datetime.now(UTC) - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    with sqlite3.connect(enrollment_db) as conn:
        conn.execute(
            "UPDATE compute_enrollment_tokens SET expires_at = ? WHERE token_id = ?",
            (expired_at, created.token_id),
        )
        conn.commit()

    errors: list[str] = []
    for token in (created.token, "x" * 43):
        with pytest.raises(enrollment.EnrollmentError) as exc_info:
            enrollment.consume_token(token)
        errors.append(exc_info.value.code)
    assert errors == ["enrollment_invalid", "enrollment_invalid"]


@pytest.mark.parametrize("ttl", [0, 3601])
def test_enrollment_token_ttl_is_bounded(enrollment_db: Path, ttl: int) -> None:
    with pytest.raises(ValueError, match="ttl"):
        enrollment.create_token(requested_name="Node A", created_by="admin", ttl_seconds=ttl)
