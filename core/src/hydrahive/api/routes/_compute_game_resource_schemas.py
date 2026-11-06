"""Strict request schemas for Core Game Studio resource routes."""

from pydantic import BaseModel, ConfigDict, Field


class IsolationApprovalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(min_length=1, max_length=128)
    isolation_profile_id: str = Field(min_length=1, max_length=128)
    runner_version: str = Field(min_length=1, max_length=128)
    policy_digest: str = Field(min_length=1, max_length=255)
    proof_digest: str = Field(min_length=1, max_length=255)


class GameResourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(min_length=1, max_length=128)
    workspace_handle: str = Field(min_length=1, max_length=255)
    engine: str = Field(pattern="^(unknown|godot|unreal)$")
    engine_version: str | None = Field(default=None, max_length=128)
    engine_project_relpath: str = Field(default=".", min_length=1, max_length=1024)
    trust_mode: str = Field(pattern="^(inventory_only|sandboxed)$")
    isolation_approval_id: str = Field(min_length=1, max_length=128)
    isolation_profile_id: str = Field(min_length=1, max_length=128)
    runner_version: str = Field(min_length=1, max_length=128)
    policy_digest: str = Field(min_length=1, max_length=255)
