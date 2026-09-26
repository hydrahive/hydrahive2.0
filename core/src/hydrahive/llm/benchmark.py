"""Short, node-scoped Ollama throughput benchmarks."""
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

_MAX_JOBS = 100


async def _call_benchmark_model(model: str, **_: Any) -> dict[str, int]:
    if not model.startswith("ollama/"):
        raise ValueError("benchmark_provider_not_supported")
    cfg = load_config()
    provider = next((p for p in cfg.get("providers", []) if p.get("id") == "ollama"), None)
    api_base = provider_api_base(cfg, "ollama") if provider else None
    if not api_base:
        raise ValueError("ollama_not_configured")
    _, _, usage = await litellm_call(
        model=model,
        system_prompt="Reply briefly and plainly.",
        messages=[{"role": "user", "content": "Explain in one short sentence what a local language model is."}],
        tools=[],
        temperature=0.0,
        max_tokens=64,
        api_base=api_base,
        num_ctx=num_ctx_for_ollama(context_window_for(model)),
    )
    return usage


async def run_benchmark(model: str, *, node_id: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        usage = await _call_benchmark_model(model, node_id=node_id)
        elapsed = max(time.perf_counter() - started, 0.001)
        prompt_tokens = int(usage.get("input_tokens", 0) or 0)
        completion_tokens = int(usage.get("output_tokens", 0) or 0)
        return {
            "status": "completed",
            "latency_ms": round(elapsed * 1000, 1),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "prompt_tps": round(prompt_tokens / elapsed, 2) if prompt_tokens else None,
            "completion_tps": round(completion_tokens / elapsed, 2) if completion_tokens else None,
        }
    except Exception as exc:
        return {"status": "failed", "error": str(exc)[:400]}


@dataclass
class BenchmarkJob:
    id: str
    model: str
    node_id: str
    status: str = "queued"
    result: dict[str, Any] | None = None
    error: str | None = None


_jobs: dict[str, BenchmarkJob] = {}
_tasks: dict[str, asyncio.Task] = {}
_lock = asyncio.Lock()


def _serialize(job: BenchmarkJob) -> dict[str, Any]:
    return asdict(job)


async def start_benchmark(model: str, *, node_id: str) -> dict[str, Any]:
    model = f"ollama/{normalize_model_name(model)}"
    async with _lock:
        existing = next((j for j in _jobs.values() if j.model == model and j.node_id == node_id and j.status in {"queued", "running"}), None)
        if existing:
            return _serialize(existing)
        if len(_jobs) >= _MAX_JOBS:
            for job_id, job in list(_jobs.items()):
                if job.status in {"completed", "failed"}:
                    _jobs.pop(job_id)
                    _tasks.pop(job_id, None)
                    break
        job = BenchmarkJob(id=str(uuid.uuid4()), model=model, node_id=node_id)
        _jobs[job.id] = job
        _tasks[job.id] = asyncio.create_task(_execute(job))
        return _serialize(job)


async def _execute(job: BenchmarkJob) -> None:
    job.status = "running"
    job.result = await run_benchmark(job.model, node_id=job.node_id)
    job.status = job.result.get("status", "failed")
    if job.status == "failed":
        job.error = job.result.get("error")


def get_benchmark(job_id: str) -> dict[str, Any] | None:
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
