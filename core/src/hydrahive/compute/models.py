"""Typed persistence models and bounds for the compute-cluster foundation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

NodeKind = Literal["local", "agent"]
NodeStatus = Literal["pending", "online", "degraded", "offline", "draining", "disabled", "revoked"]
JobResourceKind = Literal["container", "vm", "node"]
JobStatus = Literal["queued", "leased", "running", "succeeded", "failed", "cancelled", "expired"]
GameEngine = Literal["unknown", "godot", "unreal"]
GameTrustMode = Literal["inventory_only", "sandboxed"]
GameWorkspaceStatus = Literal["pending", "ready", "offline", "incompatible", "revoked", "error"]
IsolationApprovalStatus = Literal["active", "revoked"]
JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]

NODE_KINDS: frozenset[str] = frozenset({"local", "agent"})
JOB_RESOURCE_KINDS: frozenset[str] = frozenset({"container", "vm", "node"})
JOB_STATUSES: frozenset[str] = frozenset({"queued", "leased", "running", "succeeded", "failed", "cancelled", "expired"})
NODE_STATUSES: frozenset[str] = frozenset(
    {"pending", "online", "degraded", "offline", "draining", "disabled", "revoked"}
)
MAX_NODE_ID_LENGTH = 128
MAX_NODE_NAME_LENGTH = 255
MAX_NODE_JSON_BYTES = 64 * 1024
GAME_RUNTIME_PROVIDER = "game-runtime/v1"
GAME_ENGINES: frozenset[str] = frozenset({"unknown", "godot", "unreal"})
GAME_TRUST_MODES: frozenset[str] = frozenset({"inventory_only", "sandboxed"})
GAME_WORKSPACE_STATUSES: frozenset[str] = frozenset(
    {"pending", "ready", "offline", "incompatible", "revoked", "error"}
)


@dataclass(frozen=True, slots=True)
class ComputeNode:
    node_id: str
    name: str
    kind: NodeKind
    status: NodeStatus
    protocol_version: int
    created_at: str
    updated_at: str
    last_sequence: int = 0
    capabilities: JSONObject = field(default_factory=dict)
    resources: JSONObject = field(default_factory=dict)
    labels: JSONObject = field(default_factory=dict)
    health_errors: list[str] = field(default_factory=list)
    certificate_fingerprint: str | None = None
    agent_version: str | None = None
    last_seen_at: str | None = None
    approved_at: str | None = None
    approved_by: str | None = None
    revoked_at: str | None = None


@dataclass(frozen=True, slots=True)
class ComputeEnrollmentToken:
    token_id: str
    token_hmac: str
    requested_name: str
    expires_at: str
    created_by: str
    created_at: str
    consumed_at: str | None = None


@dataclass(frozen=True, slots=True)
class GameIsolationApproval:
    approval_id: str
    node_id: str
    isolation_profile_id: str
    runner_version: str
    policy_digest: str
    proof_digest: str
    status: IsolationApprovalStatus
    approved_by: str
    approved_at: str
    revoked_by: str | None = None
    revoked_at: str | None = None


@dataclass(frozen=True, slots=True)
class ComputeGameWorkspace:
    resource_id: str
    provider: str
    project_id: str
    node_id: str
    workspace_handle: str
    engine: GameEngine
    engine_version: str | None
    engine_project_relpath: str
    trust_mode: GameTrustMode
    status: GameWorkspaceStatus
    isolation_approval_id: str
    isolation_profile_id: str
    runner_version: str
    policy_digest: str
    generation: int
    created_by: str
    created_at: str
    updated_at: str
    last_seen_at: str | None = None
    revoked_at: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionBinding:
    """Exact, caller-supplied binding values that PR2 must validate before execution."""

    project_id: str
    resource_id: str
    node_id: str
    workspace_handle: str
    workspace_generation: int
    isolation_approval_id: str
    isolation_profile_id: str
    runner_version: str
    policy_digest: str
    proof_digest: str


@dataclass(frozen=True, slots=True)
class ComputeJob:
    job_id: str
    node_id: str
    resource_kind: JobResourceKind
    resource_id: str | None
    operation: str
    generation: int
    payload: JSONObject
    idempotency_key: str
    status: JobStatus
    attempts: int
    progress: int
    created_by: str
    created_at: str
    lease_id: str | None = None
    lease_until: str | None = None
    error_code: str | None = None
    error_params: JSONObject | None = None
    started_at: str | None = None
    finished_at: str | None = None


@dataclass(frozen=True, slots=True)
class ComputeJobEvent:
    event_id: int
    job_id: str
    sequence: int
    event_type: str
    data: JSONObject
    created_at: str
