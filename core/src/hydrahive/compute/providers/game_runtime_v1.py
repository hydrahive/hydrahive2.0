"""Strict, versioned payload contract for the ``game-runtime/v1`` provider."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import Field, TypeAdapter, model_validator

from hydrahive.compute.providers._game_runtime_payloads import (
    _DIGEST,
    _IDENTIFIER,
    BuildPayload,
    ExportPayload,
    GameRuntimeLimits,
    InspectPayload,
    InventoryPayload,
    RunObservePayload,
    StrictGameModel,
    TestPayload,
    ValidatePayload,
)

_COMMIT = r"^[0-9a-f]{40}([0-9a-f]{24})?$"


class GameOperation(StrEnum):
    INSPECT = "game.workspace.inspect"
    INVENTORY = "game.project.inventory"
    VALIDATE = "game.project.validate"
    BUILD = "game.project.build"
    TEST = "game.project.test"
    RUN_OBSERVE = "game.project.run_observe"
    EXPORT = "game.project.export"


class _GameJobRequestBase(StrictGameModel):
    game_resource_id: str = Field(pattern=_IDENTIFIER)
    source_commit_sha: str | None = Field(default=None, pattern=_COMMIT)
    source_snapshot_digest: str | None = Field(default=None, pattern=_DIGEST)
    inventory_snapshot_id: str | None = Field(default=None, pattern=_IDENTIFIER)
    engine: Literal["unknown", "godot", "unreal"]
    engine_version: str | None = Field(default=None, min_length=1, max_length=128)
    toolchain_digest: str = Field(pattern=_DIGEST)
    profile_id: str = Field(pattern=_IDENTIFIER)
    input_revision: int = Field(ge=0)
    limits: GameRuntimeLimits
    idempotency_key: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def _immutable_source_and_inventory(self):
        if (self.source_commit_sha is None) == (self.source_snapshot_digest is None):
            raise ValueError("exactly one immutable source revision is required")
        operation = self.operation
        discovery_operation = operation in {GameOperation.INSPECT, GameOperation.INVENTORY}
        if discovery_operation and self.inventory_snapshot_id is not None:
            raise ValueError("inventory_snapshot_id is not allowed for discovery operations")
        if not discovery_operation and self.inventory_snapshot_id is None:
            raise ValueError("inventory_snapshot_id is required for this operation")
        if not discovery_operation and self.engine != "godot":
            raise ValueError("only Godot execution is available in game-runtime/v1")
        if not discovery_operation and self.engine_version is None:
            raise ValueError("engine_version is required for executable operations")
        return self


class InspectRequest(_GameJobRequestBase):
    operation: Literal[GameOperation.INSPECT]
    operation_payload: InspectPayload


class InventoryRequest(_GameJobRequestBase):
    operation: Literal[GameOperation.INVENTORY]
    operation_payload: InventoryPayload


class ValidateRequest(_GameJobRequestBase):
    operation: Literal[GameOperation.VALIDATE]
    operation_payload: ValidatePayload


class BuildRequest(_GameJobRequestBase):
    operation: Literal[GameOperation.BUILD]
    operation_payload: BuildPayload


class TestRequest(_GameJobRequestBase):
    operation: Literal[GameOperation.TEST]
    operation_payload: TestPayload


class RunObserveRequest(_GameJobRequestBase):
    operation: Literal[GameOperation.RUN_OBSERVE]
    operation_payload: RunObservePayload


class ExportRequest(_GameJobRequestBase):
    operation: Literal[GameOperation.EXPORT]
    operation_payload: ExportPayload


GameJobRequest: TypeAlias = Annotated[
    InspectRequest | InventoryRequest | ValidateRequest | BuildRequest | TestRequest | RunObserveRequest | ExportRequest,
    Field(discriminator="operation"),
]
_REQUEST_ADAPTER = TypeAdapter(GameJobRequest)


class GameRuntimeStoredPayload(StrictGameModel):
    schema_version: Literal[1] = 1
    workspace_handle: str = Field(pattern=_IDENTIFIER)
    isolation_approval_id: str = Field(pattern=_IDENTIFIER)
    isolation_profile_id: str = Field(pattern=_IDENTIFIER)
    runner_version: str = Field(min_length=1, max_length=128)
    policy_digest: str = Field(min_length=1, max_length=255)
    proof_digest: str = Field(min_length=1, max_length=255)
    request: GameJobRequest


class GameRuntimeOffer(StrictGameModel):
    job_id: str = Field(pattern=_IDENTIFIER)
    node_id: str = Field(pattern=_IDENTIFIER)
    resource_kind: Literal["game_workspace"]
    resource_id: str = Field(pattern=_IDENTIFIER)
    operation: Literal[
        "game.workspace.inspect", "game.project.inventory", "game.project.validate",
        "game.project.build", "game.project.test", "game.project.run_observe", "game.project.export",
    ]
    generation: int = Field(ge=1)
    payload: GameRuntimeStoredPayload
    idempotency_key: str = Field(min_length=1, max_length=255)
    lease_id: str = Field(pattern=_IDENTIFIER)
    lease_until: str = Field(min_length=1, max_length=64)
    attempt_id: str = Field(pattern=_IDENTIFIER)
    provider: Literal["game-runtime/v1"]
    project_id: str = Field(pattern=_IDENTIFIER)
    game_resource_id: str = Field(pattern=_IDENTIFIER)
    workspace_generation: int = Field(ge=1)
    source_commit_sha: str | None = Field(default=None, pattern=_COMMIT)
    source_snapshot_digest: str | None = Field(default=None, pattern=_DIGEST)

    @model_validator(mode="after")
    def _matching_persisted_bindings(self):
        request = self.payload.request
        if (self.source_commit_sha is None) == (self.source_snapshot_digest is None):
            raise ValueError("exactly one immutable source revision is required")
        if (
            self.resource_id != self.game_resource_id
            or self.generation != self.workspace_generation
            or self.attempt_id != self.lease_id
            or request.game_resource_id != self.game_resource_id
            or request.operation != self.operation
            or request.idempotency_key != self.idempotency_key
            or request.source_commit_sha != self.source_commit_sha
            or request.source_snapshot_digest != self.source_snapshot_digest
        ):
            raise ValueError("persisted game job bindings do not match")
        return self


def validate_game_job_request(value: object) -> GameJobRequest:
    """Decode a client request without coercion or unknown-field tolerance."""
    return _REQUEST_ADAPTER.validate_python(value)


def validate_stored_payload(value: object) -> GameRuntimeStoredPayload:
    return GameRuntimeStoredPayload.model_validate(value)


def validate_game_offer(value: object) -> GameRuntimeOffer:
    return GameRuntimeOffer.model_validate(value)
