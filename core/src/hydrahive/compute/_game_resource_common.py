"""Shared validation, row codecs, and errors for Game Studio resources."""

from __future__ import annotations

import sqlite3
from pathlib import PureWindowsPath

from hydrahive.compute.models import (
    GAME_ENGINES,
    GAME_TRUST_MODES,
    ComputeGameWorkspace,
    GameEngine,
    GameIsolationApproval,
    GameTrustMode,
)

MAX_ID = 128
MAX_HANDLE = 255
MAX_VERSION = 128
MAX_DIGEST = 255
EXECUTABLE_NODE_STATUSES = frozenset({"online", "degraded"})


class GameResourceError(ValueError):
    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


class ExecutionBindingError(GameResourceError):
    """A fail-closed PR2 execution-binding validation failure."""


def required(value: str, field_name: str, *, maximum: int = MAX_ID) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > maximum:
        raise ValueError(f"{field_name} must contain 1-{maximum} non-padded characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{field_name} contains control characters")
    return value


def optional_version(value: str | None) -> str | None:
    if value is None:
        return None
    return required(value, "engine_version", maximum=MAX_VERSION)


def workspace_handle(value: str) -> str:
    value = required(value, "workspace_handle", maximum=MAX_HANDLE)
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError("workspace_handle must be an opaque identifier, not a path")
    return value


def normalize_engine_project_relpath(value: str) -> str:
    """Validate a normalized, portable relative path; ``.`` means workspace root."""
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 1024:
        raise ValueError("engine_project_relpath must be a non-empty relative path")
    if value == ".":
        return value
    if value.startswith("/") or "\\" in value or PureWindowsPath(value).drive:
        raise ValueError("engine_project_relpath must be relative")
    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError("engine_project_relpath contains an unsafe segment")
    if any(any(ord(character) < 32 or ord(character) == 127 for character in segment) for segment in segments):
        raise ValueError("engine_project_relpath contains control characters")
    return value


def engine(value: str) -> GameEngine:
    if value not in GAME_ENGINES:
        raise ValueError("engine is invalid")
    return value  # type: ignore[return-value]


def trust_mode(value: str) -> GameTrustMode:
    if value not in GAME_TRUST_MODES:
        raise ValueError("trust_mode is invalid")
    return value  # type: ignore[return-value]


def approval_from_row(row: sqlite3.Row) -> GameIsolationApproval:
    return GameIsolationApproval(
        approval_id=row["approval_id"],
        node_id=row["node_id"],
        isolation_profile_id=row["isolation_profile_id"],
        runner_version=row["runner_version"],
        policy_digest=row["policy_digest"],
        proof_digest=row["proof_digest"],
        status=row["status"],
        approved_by=row["approved_by"],
        approved_at=row["approved_at"],
        revoked_by=row["revoked_by"],
        revoked_at=row["revoked_at"],
    )


def workspace_from_row(row: sqlite3.Row) -> ComputeGameWorkspace:
    return ComputeGameWorkspace(
        resource_id=row["resource_id"],
        provider=row["provider"],
        project_id=row["project_id"],
        node_id=row["node_id"],
        workspace_handle=row["workspace_handle"],
        engine=row["engine"],
        engine_version=row["engine_version"],
        engine_project_relpath=row["engine_project_relpath"],
        trust_mode=row["trust_mode"],
        status=row["status"],
        isolation_approval_id=row["isolation_approval_id"],
        isolation_profile_id=row["isolation_profile_id"],
        runner_version=row["runner_version"],
        policy_digest=row["policy_digest"],
        generation=row["generation"],
        created_by=row["created_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_seen_at=row["last_seen_at"],
        revoked_at=row["revoked_at"],
    )
