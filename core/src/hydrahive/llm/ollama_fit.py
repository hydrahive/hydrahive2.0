"""Fault-tolerant adapter for llmfit's machine-readable CLI output."""
from __future__ import annotations

import asyncio
import json
import time

# llmfit 1.1.12 liefert für ~8.800 Varianten knapp 17 MB JSON.
# Feste Obergrenze schützt den Service, ohne die reale Ausgabe abzuschneiden.
MAX_OUTPUT_BYTES = 32_000_000
_TIMEOUT_SECONDS = 30
_CACHE_TTL = 300
_FIT_LEVELS = {"perfect", "good", "marginal", "too_tight"}
_cache: tuple[float, dict] | None = None
_cache_lock = asyncio.Lock()


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


def free_vram_gib(system: dict | None) -> float | None:
    """Freier GPU-Speicher aus dem llmfit-system-Block. None wenn unbekannt.

    llmfit meldet `gpu_available_gb` (frei) und `gpu_vram_gb` (gesamt). Für die
    num_ctx-Budgetierung zählt der freie Speicher; fehlt er, ist der Gesamtwert
    die schlechtere, aber immer noch brauchbare Näherung.
    """
    if not isinstance(system, dict):
        return None
    for key in ("gpu_available_gb", "gpu_vram_gb"):
        value = system.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


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


async def _load_uncached() -> dict:
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


async def load_hardware_fit() -> dict:
    global _cache
    if _cache and time.monotonic() - _cache[0] < _CACHE_TTL:
        return _cache[1]
    async with _cache_lock:
        if _cache and time.monotonic() - _cache[0] < _CACHE_TTL:
            return _cache[1]
        result = await _load_uncached()
        _cache = (time.monotonic(), result)
        return result


def cached_system() -> dict | None:
    """Sync, ohne Subprozess: der zuletzt ermittelte llmfit-system-Block.

    Für synchrone Aufrufer (z.B. context_window_for), die den freien VRAM
    brauchen, aber niemals einen llmfit-Lauf auslösen dürfen. None, solange
    der asynchrone Katalogpfad noch nichts ermittelt hat.
    """
    return _cache[1].get("system") if _cache else None


def _cache_clear() -> None:
    global _cache, _cache_lock
    _cache = None
    _cache_lock = asyncio.Lock()
