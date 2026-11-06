from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from hydrahive.compute.providers.game_runtime_v1 import validate_game_job_request


SOURCE_COMMIT = "a" * 40
DIGEST = "sha256:" + "b" * 64


def _request(operation: str, operation_payload: dict) -> dict:
    return {
        "game_resource_id": "resource-a",
        "operation": operation,
        "source_commit_sha": SOURCE_COMMIT,
        "source_snapshot_digest": None,
        "inventory_snapshot_id": None if operation in {"game.workspace.inspect", "game.project.inventory"} else "inventory-a",
        "engine": "godot",
        "engine_version": "4.5.1",
        "toolchain_digest": DIGEST,
        "profile_id": "debug-desktop",
        "input_revision": 12,
        "limits": {
            "timeout_seconds": 900,
            "cpu_cores": 4,
            "memory_mb": 8192,
            "disk_mb": 16384,
            "pids": 256,
            "network": "off",
        },
        "operation_payload": operation_payload,
        "idempotency_key": f"request:{operation}",
    }


@pytest.mark.parametrize(
    ("operation", "payload"),
    [
        ("game.workspace.inspect", {"privacy": "summary"}),
        (
            "game.project.inventory",
            {"scan_profile_id": "safe-default", "include_hashes": True, "max_files": 10000, "max_bytes": 1000000},
        ),
        ("game.project.validate", {"validation_profile_id": "validation-default"}),
        ("game.project.build", {"target_id": "linux", "configuration_id": "debug"}),
        ("game.project.test", {"suite_id": "smoke"}),
        (
            "game.project.run_observe",
            {
                "artifact_id": "artifact-a",
                "artifact_digest": DIGEST,
                "artifact_handle": "opaque-artifact-a",
                "scenario_id": "boot_smoke",
                "evidence": "screenshot",
            },
        ),
        ("game.project.export", {"preset_id": "linux-desktop", "destination": "server_upload"}),
    ],
)
def test_game_runtime_v1_accepts_only_closed_operations(operation: str, payload: dict) -> None:
    parsed = validate_game_job_request(_request(operation, payload))

    assert parsed.operation == operation
    assert parsed.operation_payload.model_dump(mode="json") == payload


@pytest.mark.parametrize("field", ["shell", "command", "host_path", "mounts", "env", "secrets"])
def test_game_runtime_v1_rejects_unknown_and_dangerous_fields(field: str) -> None:
    request = _request("game.project.validate", {"validation_profile_id": "validation-default"})
    request[field] = "forbidden"

    with pytest.raises(ValidationError):
        validate_game_job_request(request)


@pytest.mark.parametrize("field", ["command", "args", "host_path", "mounts", "env", "secret"])
def test_game_runtime_v1_rejects_unknown_operation_payload_fields(field: str) -> None:
    request = _request("game.project.test", {"suite_id": "smoke", field: "forbidden"})

    with pytest.raises(ValidationError):
        validate_game_job_request(request)


def test_game_runtime_v1_requires_exactly_one_immutable_source() -> None:
    missing = _request("game.project.validate", {"validation_profile_id": "validation-default"})
    missing["source_commit_sha"] = None
    with pytest.raises(ValidationError):
        validate_game_job_request(missing)

    duplicate = copy.deepcopy(missing)
    duplicate["source_commit_sha"] = SOURCE_COMMIT
    duplicate["source_snapshot_digest"] = DIGEST
    with pytest.raises(ValidationError):
        validate_game_job_request(duplicate)


def test_game_runtime_v1_enforces_inventory_and_engine_scope() -> None:
    discovery = _request("game.workspace.inspect", {"privacy": "summary"})
    discovery["inventory_snapshot_id"] = "inventory-not-allowed"
    with pytest.raises(ValidationError):
        validate_game_job_request(discovery)

    unreal_execution = _request("game.project.validate", {"validation_profile_id": "validation-default"})
    unreal_execution["engine"] = "unreal"
    with pytest.raises(ValidationError):
        validate_game_job_request(unreal_execution)

    missing_version = _request("game.project.build", {"target_id": "linux", "configuration_id": "debug"})
    missing_version["engine_version"] = None
    with pytest.raises(ValidationError):
        validate_game_job_request(missing_version)


def test_game_runtime_v1_rejects_unknown_operation_and_non_strict_values() -> None:
    unknown = _request("game.project.shell", {})
    with pytest.raises(ValidationError):
        validate_game_job_request(unknown)

    coerced = _request("game.project.inventory", {
        "scan_profile_id": "safe-default",
        "include_hashes": "yes",
        "max_files": 100,
        "max_bytes": 1000,
    })
    with pytest.raises(ValidationError):
        validate_game_job_request(coerced)
