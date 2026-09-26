"""Safe, node-scoped capability probes for chat models.

The probe deliberately bypasses the normal capability gate: its purpose is to
find out whether a model can emit a native tool call, not to trust a registry
claim. The only dispatched function is a local no-op echo.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import time
import uuid
from typing import Any

from hydrahive.compaction.tokens import context_window_for
from hydrahive.llm._config import load_config, num_ctx_for_ollama, provider_api_base
from hydrahive.llm.ollama_common import normalize_model_name
from hydrahive.runner._llm_bridge_backends import litellm_call

PROBE_VERSION = 1
PROBE_TOOL_NAME = "catalog_probe_echo"
_MAX_JOBS = 100

_TOOL_SCHEMA = {
    "name": PROBE_TOOL_NAME,
    "description": "Internal no-op catalog verification tool. Never performs external actions.",
    "input_schema": {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
    },
}


def _declared(model: str) -> bool | None:
    from hydrahive.llm import registry

    if registry._cache:
        for entry in registry._cache[1]:
            if entry.id == model:
                return entry.tool_use
    return None


async def _call_probe_model(model: str, **_: Any) -> tuple[list[dict], str, dict[str, int]]:
    """Call Ollama directly through the shared LiteLLM conversion path."""
    if not model.startswith("ollama/"):
        raise ValueError("probe_provider_not_supported")
    cfg = load_config()
    provider = next((p for p in cfg.get("providers", []) if p.get("id") == "ollama"), None)
    if not provider or not provider_api_base(cfg, "ollama"):
        raise ValueError("ollama_not_configured")
    return await litellm_call(
        model=model,
        system_prompt=(
            "You are a capability probe. Emit exactly one native function call "
            "to catalog_probe_echo with value=ok. Do not write a textual JSON imitation."
        ),
        messages=[{"role": "user", "content": "Perform the capability probe now."}],
        tools=[_TOOL_SCHEMA],
        temperature=0.0,
        max_tokens=128,
        api_base=provider_api_base(cfg, "ollama"),
        num_ctx=num_ctx_for_ollama(context_window_for(model)),
    )


def _tool_result(blocks: list[dict]) -> dict[str, Any] | None:
    for block in blocks:
        if (
            isinstance(block, dict)
            and block.get("type") == "tool_use"
            and block.get("name") == PROBE_TOOL_NAME
        ):
            return block
    return None


async def probe_tools(model: str, *, node_id: str) -> dict[str, Any]:
    declared = _declared(model)
    result: dict[str, Any] = {
        "status": "unknown",
        "declared": declared,
        "verified_at": None,
        "probe_version": PROBE_VERSION,
        "details": None,
    }
    try:
        blocks, _, _ = await _call_probe_model(model, node_id=node_id, tools=[_TOOL_SCHEMA])
        block = _tool_result(blocks)
        if not block or (block.get("input") or {}).get("value") != "ok":
            result.update(status="failed", details="no_native_tool_call")
            return result
        # Safe local dispatch: no user tool registry, filesystem, shell or network.
        result.update(
            status="verified",
            verified_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            details="native_tool_call_and_safe_dispatch",
        )
    except Exception:
        result.update(status="failed", details="probe_failed")
    return result


@dataclass
class ProbeJob:
    id: str
    model: str
    node_id: str
    status: str = "queued"
    result: dict[str, Any] | None = None
    error: str | None = None


_jobs: dict[str, ProbeJob] = {}
_tasks: dict[str, asyncio.Task] = {}
_lock = asyncio.Lock()


def _serialize(job: ProbeJob) -> dict[str, Any]:
    return asdict(job)


async def start_probe(model: str, *, node_id: str) -> dict[str, Any]:
    model = f"ollama/{normalize_model_name(model)}"
    async with _lock:
        existing = next((j for j in _jobs.values() if j.model == model and j.node_id == node_id and j.status in {"queued", "running"}), None)
        if existing:
            return _serialize(existing)
        if len(_jobs) >= _MAX_JOBS:
            for job_id, job in list(_jobs.items()):
                if job.status in {"success", "failed"}:
                    _jobs.pop(job_id)
                    _tasks.pop(job_id, None)
                    break
        job = ProbeJob(id=str(uuid.uuid4()), model=model, node_id=node_id)
        _jobs[job.id] = job
        _tasks[job.id] = asyncio.create_task(_execute(job))
        return _serialize(job)


async def _execute(job: ProbeJob) -> None:
    job.status = "running"
    job.result = await probe_tools(job.model, node_id=job.node_id)
    job.status = "success" if job.result.get("status") == "verified" else "failed"


def get_probe(job_id: str) -> dict[str, Any] | None:
    job = _jobs.get(job_id)
    return _serialize(job) if job else None


def _reset_jobs() -> None:
    global _lock
    for task in _tasks.values():
        if not task.done():
            task.cancel()
    _jobs.clear()
    _tasks.clear()
    _lock = asyncio.Lock()
