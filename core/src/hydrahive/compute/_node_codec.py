"""Validation and row/JSON conversion for compute-node persistence."""

from __future__ import annotations

import json
import sqlite3
from typing import cast

from hydrahive.compute.models import (
    MAX_NODE_ID_LENGTH,
    MAX_NODE_JSON_BYTES,
    MAX_NODE_NAME_LENGTH,
    NODE_KINDS,
    NODE_STATUSES,
    ComputeNode,
    JSONObject,
    NodeKind,
    NodeStatus,
)

ALLOWED_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"online", "disabled", "revoked"}),
    "online": frozenset({"degraded", "offline", "draining", "disabled", "revoked"}),
    "degraded": frozenset({"online", "offline", "draining", "disabled", "revoked"}),
    "offline": frozenset({"online", "degraded", "draining", "disabled", "revoked"}),
    "draining": frozenset({"online", "offline", "disabled", "revoked"}),
    "disabled": frozenset({"online", "offline", "revoked"}),
    "revoked": frozenset(),
}


def validate_identity(node_id: str, name: str) -> None:
    if not node_id or len(node_id) > MAX_NODE_ID_LENGTH:
        raise ValueError(f"node_id must contain 1-{MAX_NODE_ID_LENGTH} characters")
    if not name or len(name) > MAX_NODE_NAME_LENGTH:
        raise ValueError(f"name must contain 1-{MAX_NODE_NAME_LENGTH} characters")


def validate_kind(kind: str) -> NodeKind:
    if kind not in NODE_KINDS:
        raise ValueError(f"invalid node kind: {kind}")
    return cast(NodeKind, kind)


def validate_status(status: str) -> NodeStatus:
    if status not in NODE_STATUSES:
        raise ValueError(f"invalid node status: {status}")
    return cast(NodeStatus, status)


def dump_json(value: JSONObject, field_name: str) -> str:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must contain valid JSON") from exc
    if len(encoded.encode("utf-8")) > MAX_NODE_JSON_BYTES:
        raise ValueError(f"{field_name} JSON is too large")
    return encoded


def load_json(value: str, field_name: str) -> JSONObject:
    decoded = json.loads(value)
    if not isinstance(decoded, dict):
        raise ValueError(f"stored {field_name} must be a JSON object")
    return cast(JSONObject, decoded)


def row_to_node(row: sqlite3.Row) -> ComputeNode:
    return ComputeNode(
        node_id=row["node_id"],
        name=row["name"],
        kind=validate_kind(row["kind"]),
        status=validate_status(row["status"]),
        certificate_fingerprint=row["certificate_fingerprint"],
        protocol_version=row["protocol_version"],
        agent_version=row["agent_version"],
        capabilities=load_json(row["capabilities_json"], "capabilities"),
        resources=load_json(row["resources_json"], "resources"),
        labels=load_json(row["labels_json"], "labels"),
        last_seen_at=row["last_seen_at"],
        approved_at=row["approved_at"],
        approved_by=row["approved_by"],
        revoked_at=row["revoked_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
