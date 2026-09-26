"""Safe in-process lifecycle jobs for native Ollama model pulls and deletes."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import json
import re
import time
import uuid

import httpx

from hydrahive.agents import config as agent_config
from hydrahive.llm import ollama_client, registry
from hydrahive.llm._config import load_config
from hydrahive.llm.ollama_common import normalize_model_name

_MAX_LINE_BYTES = 65_536
_MAX_JOBS = 100
_TERMINAL = {"success", "failed"}
_jobs: dict[str, "PullJob"] = {}
_tasks: dict[str, asyncio.Task] = {}
_job_lock = asyncio.Lock()


class PullFailed(RuntimeError):
    pass


class ModelInUse(RuntimeError):
    def __init__(self, references: list[str]):
        self.references = references
        super().__init__("ollama_model_in_use")


@dataclass
class PullJob:
    id: str
    model: str
    status: str = "queued"
    phase: str = "queued"
    total: int | None = None
    completed: int | None = None
    error: str | None = None
    created_at: float = 0.0
    updated_at: float = 0.0

    def __post_init__(self) -> None:
        now = time.time()
        self.created_at = self.created_at or now
        self.updated_at = self.updated_at or now


def _serialize(job: PullJob) -> dict:
    return asdict(job)


def _safe_phase(value: object) -> str:
    phase = re.sub(r"[^a-zA-Z0-9 ._:/-]", "", str(value or "pulling"))[:100].strip()
    return phase or "pulling"


def _apply_progress(job: PullJob, line: str) -> None:
    if len(line.encode()) > _MAX_LINE_BYTES:
        raise PullFailed("ollama_pull_failed")
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        raise PullFailed("ollama_pull_failed") from None
    if not isinstance(payload, dict) or payload.get("error"):
        raise PullFailed("ollama_pull_failed")
    job.status = "pulling"
    job.phase = _safe_phase(payload.get("status"))
    if isinstance(payload.get("total"), int):
        job.total = payload["total"]
    if isinstance(payload.get("completed"), int):
        job.completed = payload["completed"]
    job.updated_at = time.time()


async def _run_pull(provider: dict, job: PullJob) -> None:
    base = ollama_client.normalized_base_url(provider)
    headers = ollama_client.auth_headers(provider)
    async with httpx.AsyncClient(timeout=None, follow_redirects=False) as client:
        async with client.stream(
            "POST",
            f"{base}/api/pull",
            headers=headers,
            json={"model": job.model, "stream": True},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    _apply_progress(job, line)
    job.status = "success"
    job.phase = "success"
    job.updated_at = time.time()
    registry.invalidate()


async def _execute_pull(provider: dict, job: PullJob) -> None:
    try:
        await _run_pull(provider, job)
    except asyncio.CancelledError:
        job.status = "failed"
        job.phase = "cancelled"
        job.error = "ollama_pull_cancelled"
        raise
    except Exception:
        job.status = "failed"
        job.phase = "failed"
        job.error = "ollama_pull_failed"
        job.updated_at = time.time()


def _prune_jobs() -> None:
    if len(_jobs) < _MAX_JOBS:
        return
    terminal = sorted((j for j in _jobs.values() if j.status in _TERMINAL), key=lambda j: j.updated_at)
    for job in terminal[: max(1, len(_jobs) - _MAX_JOBS + 1)]:
        _jobs.pop(job.id, None)
        _tasks.pop(job.id, None)


async def start_pull(provider: dict, model: str) -> dict:
    name = normalize_model_name(model)
    async with _job_lock:
        existing = next((j for j in _jobs.values() if j.model == name and j.status not in _TERMINAL), None)
        if existing:
            return _serialize(existing)
        _prune_jobs()
        job = PullJob(id=str(uuid.uuid4()), model=name)
        _jobs[job.id] = job
        _tasks[job.id] = asyncio.create_task(_execute_pull(provider, job))
        return _serialize(job)


def get_pull(job_id: str) -> dict | None:
    job = _jobs.get(job_id)
    return _serialize(job) if job else None


def _matches(value: object, model: str) -> bool:
    return str(value or "") in {model, f"ollama/{model}"}


def model_references(model: str) -> list[str]:
    name = normalize_model_name(model)
    cfg = load_config()
    refs: list[str] = []
    if _matches(cfg.get("default_model"), name):
        refs.append("Standardmodell")
    if _matches(cfg.get("embed_model"), name):
        refs.append("Embedding-Modell")
    if any(_matches(value, name) for value in (cfg.get("media_models") or {}).values()):
        refs.append("Medienmodell")
    provider = next((p for p in cfg.get("providers", []) if p.get("id") == "ollama"), {})
    if any(_matches(value, name) for value in provider.get("models", [])):
        refs.append("Ollama-Providerliste")
    for agent in agent_config.list_all():
        used = _matches(agent.get("llm_model"), name) or _matches(agent.get("compact_model"), name)
        used = used or any(_matches(value, name) for value in agent.get("fallback_models", []))
        if used:
            refs.append(f"Agent: {str(agent.get('name') or agent.get('id') or 'Unbekannt')[:80]}")
    return refs


async def delete_model(provider: dict, model: str) -> None:
    name = normalize_model_name(model)
    references = model_references(name)
    if references:
        raise ModelInUse(references)
    await ollama_client.delete_model(provider, name)
    registry.invalidate()


def _reset_jobs() -> None:
    global _job_lock
    for task in _tasks.values():
        if not task.done():
            task.cancel()
    _jobs.clear()
    _tasks.clear()
    _job_lock = asyncio.Lock()
