"""Strict operation-payload validation for ``game-runtime/v1`` jobs."""

from __future__ import annotations

import re

IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

GAME_OPERATIONS = frozenset(
    {
        "game.workspace.inspect",
        "game.project.inventory",
        "game.project.validate",
        "game.project.build",
        "game.project.test",
        "game.project.run_observe",
        "game.project.export",
    }
)


class GameSchemaError(ValueError):
    pass


def exact_object(value: object, fields: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != fields:
        raise GameSchemaError(f"{label} schema is invalid")
    return value


def identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or IDENTIFIER_RE.fullmatch(value) is None:
        raise GameSchemaError(f"{label} is invalid")
    return value


def digest(value: object, label: str) -> str:
    if not isinstance(value, str) or DIGEST_RE.fullmatch(value) is None:
        raise GameSchemaError(f"{label} is invalid")
    return value


def strict_int(value: object, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise GameSchemaError(f"{label} is invalid")
    return value


def strict_bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise GameSchemaError(f"{label} is invalid")
    return value


def validate_limits(value: object) -> dict[str, object]:
    limits = exact_object(
        value,
        {"timeout_seconds", "cpu_cores", "memory_mb", "disk_mb", "pids", "network"},
        "game limits",
    )
    strict_int(limits["timeout_seconds"], "timeout_seconds", 1, 7200)
    strict_int(limits["cpu_cores"], "cpu_cores", 1, 64)
    strict_int(limits["memory_mb"], "memory_mb", 256, 262_144)
    strict_int(limits["disk_mb"], "disk_mb", 256, 1_048_576)
    strict_int(limits["pids"], "pids", 16, 4096)
    if limits["network"] != "off":
        raise GameSchemaError("game network policy is invalid")
    return limits


def validate_operation_payload(operation: str, value: object) -> dict[str, object]:
    fields = {
        "game.workspace.inspect": {"privacy"},
        "game.project.inventory": {"scan_profile_id", "include_hashes", "max_files", "max_bytes"},
        "game.project.validate": {"validation_profile_id"},
        "game.project.build": {"target_id", "configuration_id"},
        "game.project.test": {"suite_id"},
        "game.project.run_observe": {
            "artifact_id", "artifact_digest", "artifact_handle", "scenario_id", "evidence",
        },
        "game.project.export": {"preset_id", "destination"},
    }
    if operation not in fields:
        raise GameSchemaError("game operation is not allowed")
    payload = exact_object(value, fields[operation], "game operation payload")
    if operation == "game.workspace.inspect":
        if payload["privacy"] not in {"summary", "full_names"}:
            raise GameSchemaError("privacy is invalid")
    elif operation == "game.project.inventory":
        identifier(payload["scan_profile_id"], "scan_profile_id")
        strict_bool(payload["include_hashes"], "include_hashes")
        strict_int(payload["max_files"], "max_files", 1, 1_000_000)
        strict_int(payload["max_bytes"], "max_bytes", 1, 1_099_511_627_776)
    elif operation == "game.project.validate":
        identifier(payload["validation_profile_id"], "validation_profile_id")
    elif operation == "game.project.build":
        identifier(payload["target_id"], "target_id")
        identifier(payload["configuration_id"], "configuration_id")
    elif operation == "game.project.test":
        identifier(payload["suite_id"], "suite_id")
    elif operation == "game.project.run_observe":
        identifier(payload["artifact_id"], "artifact_id")
        digest(payload["artifact_digest"], "artifact_digest")
        identifier(payload["artifact_handle"], "artifact_handle")
        if payload["scenario_id"] != "boot_smoke" or payload["evidence"] not in {"screenshot", "video"}:
            raise GameSchemaError("run_observe payload is invalid")
    else:
        identifier(payload["preset_id"], "preset_id")
        if payload["destination"] not in {"workstation", "server_upload"}:
            raise GameSchemaError("export destination is invalid")
    return payload
