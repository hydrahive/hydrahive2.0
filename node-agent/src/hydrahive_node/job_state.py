"""Crash-safe pinning, execution journal, outcomes, and delivery state."""

from __future__ import annotations

import json
from pathlib import Path

from hydrahive_node.storage import StatePaths, _atomic_write

MAX_STORED_JOBS = 10_000
MAX_PENDING_RESULTS = 1_000


def _load(path: Path, label: str) -> dict[str, dict[str, object]]:
    try:
        decoded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"persisted {label} state is invalid") from exc
    if not isinstance(decoded, dict) or not all(
        isinstance(key, str) and isinstance(value, dict) for key, value in decoded.items()
    ):
        raise RuntimeError(f"persisted {label} state is invalid")
    return decoded


def _save(path: Path, value: object) -> None:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False).encode(
        "utf-8"
    )
    _atomic_write(path, encoded, 0o600)


def save_job_signing_public_key(paths: StatePaths, public_key: str) -> None:
    if not public_key or len(public_key) > 128 or not public_key.isascii():
        raise RuntimeError("job signing public key is invalid")
    if paths.job_signing_public_key.exists():
        pinned = paths.job_signing_public_key.read_text(encoding="ascii").strip()
        if pinned != public_key:
            raise RuntimeError("job signing public key changed unexpectedly")
        return
    _atomic_write(paths.job_signing_public_key, (public_key + "\n").encode("ascii"), 0o644)


def load_job_results(paths: StatePaths) -> dict[str, dict[str, object]]:
    return _load(paths.job_results, "job result")


def save_job_result(paths: StatePaths, idempotency_key: str, result: dict[str, object]) -> None:
    results = load_job_results(paths)
    existing = results.get(idempotency_key)
    if existing is not None and existing != result:
        raise RuntimeError("persisted job result conflicts with completed operation")
    results[idempotency_key] = result
    if len(results) > MAX_PENDING_RESULTS:
        raise RuntimeError("too many undelivered job results")
    _save(paths.job_results, results)


def load_job_executions(paths: StatePaths) -> dict[str, dict[str, object]]:
    return _load(paths.job_executions, "job execution")


def prepare_job_execution(paths: StatePaths, job: dict[str, object]) -> None:
    key = job.get("idempotency_key")
    if not isinstance(key, str):
        raise RuntimeError("job execution identity is invalid")
    executions = load_job_executions(paths)
    existing = executions.get(key)
    if existing is not None:
        if existing.get("job") != job:
            raise RuntimeError("idempotency key is bound to a different job")
        return
    executions[key] = {"state": "accepted", "job": job}
    _save(paths.job_executions, executions)


def mark_job_in_progress(paths: StatePaths, idempotency_key: str) -> None:
    executions = load_job_executions(paths)
    execution = executions.get(idempotency_key)
    if execution is None:
        raise RuntimeError("job execution was not prepared")
    execution["state"] = "in_progress"
    _save(paths.job_executions, executions)


def _load_delivered_list(paths: StatePaths) -> list[str]:
    try:
        decoded = json.loads(paths.delivered_jobs.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        raise RuntimeError("delivered job state is invalid") from exc
    if not isinstance(decoded, list) or not all(isinstance(item, str) for item in decoded):
        raise RuntimeError("delivered job state is invalid")
    return decoded


def load_delivered_jobs(paths: StatePaths) -> set[str]:
    return set(_load_delivered_list(paths))


def mark_job_result_delivered(paths: StatePaths, idempotency_key: str) -> None:
    delivered = _load_delivered_list(paths)
    if idempotency_key not in delivered:
        delivered.append(idempotency_key)
    delivered = delivered[-MAX_STORED_JOBS:]
    _save(paths.delivered_jobs, delivered)

    results = load_job_results(paths)
    results.pop(idempotency_key, None)
    _save(paths.job_results, results)
    executions = load_job_executions(paths)
    executions.pop(idempotency_key, None)
    _save(paths.job_executions, executions)
