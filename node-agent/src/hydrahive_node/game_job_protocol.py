"""Strict signed-envelope contracts for Game Studio jobs and cancellation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from hydrahive_node._game_payloads import (
    GAME_OPERATIONS,
    GameSchemaError,
    digest,
    exact_object,
    identifier,
    strict_int,
    validate_limits,
    validate_operation_payload,
)

COMMIT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
GAME_OFFER_FIELDS = {
    "job_id", "node_id", "resource_kind", "resource_id", "operation", "generation", "payload",
    "idempotency_key", "lease_id", "lease_until", "provider", "project_id", "game_resource_id",
    "workspace_generation", "source_commit_sha", "source_snapshot_digest", "attempt_id",
}
REQUEST_FIELDS = {
    "game_resource_id", "operation", "source_commit_sha", "source_snapshot_digest", "inventory_snapshot_id",
    "engine", "engine_version", "toolchain_digest", "profile_id", "input_revision", "limits",
    "operation_payload", "idempotency_key",
}
STORED_PAYLOAD_FIELDS = {
    "schema_version", "workspace_handle", "isolation_approval_id", "isolation_profile_id",
    "runner_version", "policy_digest", "proof_digest", "request",
}
CANCEL_FIELDS = {"job_id", "node_id", "lease_id", "cancel_deadline"}


@dataclass(frozen=True, slots=True)
class VerifiedGameJob:
    job_id: str
    node_id: str
    resource_kind: str
    resource_id: str
    operation: str
    generation: int
    payload: dict[str, object]
    idempotency_key: str
    lease_id: str
    lease_until: str
    attempt_id: str
    provider: str
    project_id: str
    game_resource_id: str
    workspace_generation: int
    source_commit_sha: str | None
    source_snapshot_digest: str | None


@dataclass(frozen=True, slots=True)
class VerifiedCancel:
    job_id: str
    node_id: str
    lease_id: str
    cancel_deadline: str


def _source(commit: object, snapshot: object) -> tuple[str | None, str | None]:
    if (commit is None) == (snapshot is None):
        raise GameSchemaError("exactly one immutable source revision is required")
    if commit is not None and (not isinstance(commit, str) or COMMIT_RE.fullmatch(commit) is None):
        raise GameSchemaError("source_commit_sha is invalid")
    if snapshot is not None:
        digest(snapshot, "source_snapshot_digest")
    return commit, snapshot  # type: ignore[return-value]


def _request(
    value: object,
    operation: str,
    resource_id: str,
    idempotency_key: object,
    commit: str | None,
    snapshot: str | None,
) -> None:
    request = exact_object(value, REQUEST_FIELDS, "game request")
    if request["operation"] != operation or request["game_resource_id"] != resource_id:
        raise GameSchemaError("game request binding does not match")
    if request["source_commit_sha"] != commit or request["source_snapshot_digest"] != snapshot:
        raise GameSchemaError("game source binding does not match")
    inventory = request["inventory_snapshot_id"]
    if operation in {"game.workspace.inspect", "game.project.inventory"}:
        if inventory is not None:
            raise GameSchemaError("inventory_snapshot_id is not allowed for discovery operations")
    else:
        identifier(inventory, "inventory_snapshot_id")
    engine = request["engine"]
    if engine not in {"unknown", "godot", "unreal"}:
        raise GameSchemaError("engine is invalid")
    version = request["engine_version"]
    if version is not None and (not isinstance(version, str) or not 0 < len(version) <= 128):
        raise GameSchemaError("engine_version is invalid")
    discovery = operation in {"game.workspace.inspect", "game.project.inventory"}
    if not discovery and engine != "godot":
        raise GameSchemaError("only Godot execution is available in game-runtime/v1")
    if not discovery and version is None:
        raise GameSchemaError("engine_version is required for executable operations")
    digest(request["toolchain_digest"], "toolchain_digest")
    identifier(request["profile_id"], "profile_id")
    strict_int(request["input_revision"], "input_revision", 0, 9_223_372_036_854_775_807)
    validate_limits(request["limits"])
    validate_operation_payload(operation, request["operation_payload"])
    key = request["idempotency_key"]
    if not isinstance(key, str) or not 0 < len(key) <= 255 or key != idempotency_key:
        raise GameSchemaError("idempotency_key binding is invalid")


def validate_game_offer(offer: object, expected_node_id: str) -> VerifiedGameJob:
    body = exact_object(offer, GAME_OFFER_FIELDS, "game offer")
    if body["resource_kind"] != "game_workspace" or body["provider"] != "game-runtime/v1":
        raise GameSchemaError("game provider binding is invalid")
    operation = body["operation"]
    if not isinstance(operation, str) or operation not in GAME_OPERATIONS:
        raise GameSchemaError("game operation is not allowed")
    node_id = identifier(body["node_id"], "node_id")
    if node_id != expected_node_id:
        raise GameSchemaError("job belongs to a different node")
    identifier(body["job_id"], "job_id")
    resource_id = identifier(body["resource_id"], "resource_id")
    game_resource_id = identifier(body["game_resource_id"], "game_resource_id")
    generation = strict_int(body["generation"], "generation", 1, 9_223_372_036_854_775_807)
    workspace_generation = strict_int(
        body["workspace_generation"], "workspace_generation", 1, 9_223_372_036_854_775_807
    )
    if resource_id != game_resource_id or generation != workspace_generation:
        raise GameSchemaError("game resource binding does not match")
    if body["attempt_id"] != body["lease_id"]:
        raise GameSchemaError("game attempt binding does not match")
    commit, snapshot = _source(body["source_commit_sha"], body["source_snapshot_digest"])
    payload = exact_object(body["payload"], STORED_PAYLOAD_FIELDS, "stored game payload")
    if payload["schema_version"] != 1:
        raise GameSchemaError("game schema version is invalid")
    for field in (
        "workspace_handle", "isolation_approval_id", "isolation_profile_id", "runner_version",
        "policy_digest", "proof_digest",
    ):
        identifier(payload[field], field)
    _request(payload["request"], operation, resource_id, body["idempotency_key"], commit, snapshot)
    for field in ("idempotency_key", "lease_id", "lease_until"):
        value = body[field]
        if not isinstance(value, str) or not 0 < len(value) <= 255:
            raise GameSchemaError(f"{field} is invalid")
    identifier(body["project_id"], "project_id")
    return VerifiedGameJob(**body)  # type: ignore[arg-type]


def validate_cancel(body: object, expected_node_id: str, expected_job_id: str, expected_lease_id: str) -> VerifiedCancel:
    value = exact_object(body, CANCEL_FIELDS, "game cancel")
    if value["node_id"] != expected_node_id or value["job_id"] != expected_job_id:
        raise GameSchemaError("game cancel binding does not match")
    if value["lease_id"] != expected_lease_id:
        raise GameSchemaError("game cancel lease does not match")
    try:
        deadline = datetime.fromisoformat(str(value["cancel_deadline"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise GameSchemaError("game cancel deadline is invalid") from exc
    if deadline.tzinfo is None or deadline.astimezone(UTC) <= datetime.now(UTC):
        raise GameSchemaError("game cancel directive has expired")
    return VerifiedCancel(**value)  # type: ignore[arg-type]
