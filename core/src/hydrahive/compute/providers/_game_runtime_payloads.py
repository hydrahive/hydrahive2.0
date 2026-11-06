"""Closed operation payloads for the ``game-runtime/v1`` provider."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_IDENTIFIER = r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"
_DIGEST = r"^sha256:[0-9a-f]{64}$"


class StrictGameModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class GameRuntimeLimits(StrictGameModel):
    timeout_seconds: int = Field(ge=1, le=7200)
    cpu_cores: int = Field(ge=1, le=64)
    memory_mb: int = Field(ge=256, le=262144)
    disk_mb: int = Field(ge=256, le=1048576)
    pids: int = Field(ge=16, le=4096)
    network: Literal["off"]


class InspectPayload(StrictGameModel):
    privacy: Literal["summary", "full_names"]


class InventoryPayload(StrictGameModel):
    scan_profile_id: str = Field(pattern=_IDENTIFIER)
    include_hashes: bool
    max_files: int = Field(ge=1, le=1_000_000)
    max_bytes: int = Field(ge=1, le=1_099_511_627_776)


class ValidatePayload(StrictGameModel):
    validation_profile_id: str = Field(pattern=_IDENTIFIER)


class BuildPayload(StrictGameModel):
    target_id: str = Field(pattern=_IDENTIFIER)
    configuration_id: str = Field(pattern=_IDENTIFIER)


class TestPayload(StrictGameModel):
    suite_id: str = Field(pattern=_IDENTIFIER)


class RunObservePayload(StrictGameModel):
    artifact_id: str = Field(pattern=_IDENTIFIER)
    artifact_digest: str = Field(pattern=_DIGEST)
    artifact_handle: str = Field(pattern=_IDENTIFIER)
    scenario_id: Literal["boot_smoke"]
    evidence: Literal["screenshot", "video"]


class ExportPayload(StrictGameModel):
    preset_id: str = Field(pattern=_IDENTIFIER)
    destination: Literal["workstation", "server_upload"]
