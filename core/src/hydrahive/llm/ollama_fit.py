"""Fault-tolerant adapter for llmfit's machine-readable CLI output."""
from __future__ import annotations

import asyncio
import json

MAX_OUTPUT_BYTES = 16_000_000
_TIMEOUT_SECONDS = 30
_FIT_LEVELS = {"perfect", "good", "marginal", "too_tight"}


async def _run_json(*args: str) -> object:
    process = await asyncio.create_subprocess_exec(
        "llmfit",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=_TIMEOUT_SECONDS)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise ValueError("llmfit_timeout") from None
    if len(stdout) > MAX_OUTPUT_BYTES or len(stderr) > MAX_OUTPUT_BYTES:
        raise ValueError("llmfit_output_too_large")
    if process.returncode != 0:
        raise ValueError("llmfit_command_failed")
    try:
        return json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        raise ValueError("llmfit_invalid_json") from None


def _rows(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("models", "recommendations", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def _system(payload: object) -> dict | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("system")
    return value if isinstance(value, dict) else payload


def _fit_code(value: object) -> str:
    code = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return code if code in _FIT_LEVELS else "unknown"


def _normalize_fit(row: dict) -> tuple[str, dict] | None:
    name = str(row.get("ollama_name") or "").strip()
    if not name:
        return None
    return name, {
        "fit": _fit_code(row.get("fit_level") or row.get("fit")),
        "score": row.get("score"),
        "memory_required_gb": row.get("memory_required_gb"),
        "memory_available_gb": row.get("memory_available_gb"),
        "estimated_tps": row.get("estimated_tps"),
        "measured_tps": row.get("measured_tps"),
        "estimate_confidence": row.get("estimate_confidence"),
        "run_mode": row.get("run_mode"),
        "best_quant": row.get("best_quant"),
    }


async def load_hardware_fit() -> dict:
    try:
        system_payload, fit_payload = await asyncio.gather(
            _run_json("system", "--json"),
            _run_json("fit", "--json"),
        )
    except FileNotFoundError:
        return {"available": False, "reason": "llmfit_not_installed", "system": None, "models": {}}
    except Exception:
        return {"available": False, "reason": "llmfit_failed", "system": None, "models": {}}

    models: dict[str, dict] = {}
    for row in _rows(fit_payload):
        normalized = _normalize_fit(row)
        if normalized:
            models[normalized[0]] = normalized[1]
    return {"available": True, "reason": None, "system": _system(system_payload), "models": models}
