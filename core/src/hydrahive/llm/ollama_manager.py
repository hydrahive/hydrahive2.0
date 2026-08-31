"""Orchestration layer joining Ollama Library, local state and llmfit."""
from __future__ import annotations

import asyncio

from hydrahive.llm import ollama_client, ollama_fit, ollama_library
from hydrahive.llm._config import load_config
from hydrahive.llm.ollama_common import validate_family_name

_FIT_DEFAULTS = {
    "fit": "unknown",
    "score": None,
    "memory_required_gb": None,
    "memory_available_gb": None,
    "estimated_tps": None,
    "measured_tps": None,
    "estimate_confidence": None,
    "run_mode": None,
    "best_quant": None,
}


def configured_provider() -> dict | None:
    return next((p for p in load_config().get("providers", []) if p.get("id") == "ollama"), None)


def _merge_fit(model: dict, fit_models: dict[str, dict]) -> dict:
    return {**_FIT_DEFAULTS, **model, **fit_models.get(model["ollama_name"], {})}


def _hardware_summary(fit: dict) -> dict:
    return {
        "available": bool(fit.get("available")),
        "reason": fit.get("reason"),
        "system": fit.get("system"),
    }


async def catalog_overview(provider: dict | None = None) -> dict:
    provider = provider or configured_provider()
    fit_task = asyncio.create_task(ollama_fit.load_hardware_fit())
    family_task = asyncio.create_task(ollama_library.list_families())
    local_task = asyncio.create_task(ollama_client.list_installed(provider)) if provider else None

    connected = False
    connection_error = "ollama_not_configured" if not provider else None
    installed: list[dict] = []
    if local_task:
        try:
            installed = await local_task
            connected = True
            connection_error = None
        except Exception as exc:
            connection_error = str(exc) if str(exc).startswith("ollama_") else "ollama_unreachable"

    library_error = None
    try:
        families = await family_task
    except Exception:
        families = []
        library_error = "ollama_library_unavailable"

    fit = await fit_task
    fit_models = fit.get("models") or {}
    installed = [_merge_fit(row, fit_models) for row in installed]
    installed_by_family: dict[str, list[str]] = {}
    for row in installed:
        installed_by_family.setdefault(row["ollama_name"].split(":", 1)[0], []).append(row["ollama_name"])
    for family in families:
        names = installed_by_family.get(family["name"], [])
        family["installed_count"] = len(names)
        family["installed_models"] = names

    return {
        "configured": provider is not None,
        "connected": connected,
        "connection_error": connection_error,
        "library_error": library_error,
        "hardware_fit": _hardware_summary(fit),
        "families": families,
        "installed_models": installed,
    }


def _variant_from_library(row: dict, capabilities: list[str]) -> dict:
    name = row["name"]
    return {
        "id": f"ollama/{name}",
        "ollama_name": name,
        "installed": False,
        "family": name.split(":", 1)[0],
        "size": row.get("size"),
        "digest": "",
        "modified_at": None,
        "parameter_size": name.split(":", 1)[1] if ":" in name else None,
        "quantization": None,
        "context_window": row.get("context_window"),
        "capabilities": list(capabilities),
        "input_modalities": row.get("input_modalities") or [],
        "output_modalities": ["embedding"] if "embedding" in capabilities else ["text"],
    }


async def family_variants(family: str, provider: dict | None = None) -> dict:
    family = validate_family_name(family)
    provider = provider or configured_provider()
    tags_task = asyncio.create_task(ollama_library.list_tags(family))
    families_task = asyncio.create_task(ollama_library.list_families())
    fit_task = asyncio.create_task(ollama_fit.load_hardware_fit())
    local_task = asyncio.create_task(ollama_client.list_installed(provider)) if provider else None

    tags, families, fit = await asyncio.gather(tags_task, families_task, fit_task)
    local: list[dict] = []
    if local_task:
        try:
            local = await local_task
        except Exception:
            pass
    family_row = next((row for row in families if row["name"] == family), None)
    capabilities = (family_row or {}).get("capabilities") or []
    local_by_name = {row["ollama_name"]: row for row in local}
    models = []
    for tag in tags:
        base = _variant_from_library(tag, capabilities)
        installed = local_by_name.get(base["ollama_name"])
        if installed:
            base.update(installed)
            base["capabilities"] = sorted(set(capabilities) | set(installed.get("capabilities") or []))
        models.append(_merge_fit(base, fit.get("models") or {}))
    return {"family": family_row or {"name": family}, "models": models}
