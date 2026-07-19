"""Crash-safe pinning, outcomes, and delivery state for compute jobs."""

from __future__ import annotations

import json

from hydrahive_node.storage import StatePaths, _atomic_write

MAX_STORED_JOBS = 10_000


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
    try:
        decoded = json.loads(paths.job_results.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise RuntimeError("persisted job results are invalid") from exc
    if not isinstance(decoded, dict) or not all(
        isinstance(key, str) and isinstance(value, dict) for key, value in decoded.items()
    ):
        raise RuntimeError("persisted job results are invalid")
    return decoded


def save_job_result(paths: StatePaths, idempotency_key: str, result: dict[str, object]) -> None:
    results = load_job_results(paths)
    existing = results.get(idempotency_key)
    if existing is not None and existing != result:
        raise RuntimeError("persisted job result conflicts with completed operation")
    results[idempotency_key] = result
    if len(results) > MAX_STORED_JOBS:
        raise RuntimeError("persisted job result limit reached")
    _atomic_write(
        paths.job_results,
        json.dumps(results, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False).encode("utf-8"),
        0o600,
    )


def load_delivered_jobs(paths: StatePaths) -> set[str]:
    try:
        decoded = json.loads(paths.delivered_jobs.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return set()
    except (OSError, ValueError) as exc:
        raise RuntimeError("delivered job state is invalid") from exc
    if not isinstance(decoded, list) or not all(isinstance(item, str) for item in decoded):
        raise RuntimeError("delivered job state is invalid")
    return set(decoded)


def mark_job_result_delivered(paths: StatePaths, idempotency_key: str) -> None:
    delivered = load_delivered_jobs(paths)
    delivered.add(idempotency_key)
    if len(delivered) > MAX_STORED_JOBS:
        raise RuntimeError("delivered job state limit reached")
    _atomic_write(
        paths.delivered_jobs,
        json.dumps(sorted(delivered), separators=(",", ":")).encode("utf-8"),
        0o600,
    )
