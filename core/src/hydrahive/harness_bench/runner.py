"""Führt die Benchmark-Aufgaben mit echtem Agenten-Runner aus und misst aus der Telemetrie.

Läuft in einem eigenen Prozess gegen dieselben Daten wie der Dienst, aber nur mit einem eigenen Benchmark-Agenten,
einem eigenen Projekt und frischen Arbeitsordnern. Keine Produktivprojekte, keine Delegation.
"""
from __future__ import annotations

import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from hydrahive.db.connection import db
from hydrahive.harness_bench.tasks import TASKS, BenchTask

BENCH_AGENT_NAME = "Harness-Benchmark"
BENCH_PROJECT_NAME = "harness-bench"
BENCH_TOOLS = ["shell_exec", "file_read", "file_write", "file_patch", "list_skills", "load_skill"]


@dataclass
class RunResult:
    task: str
    attempt: int
    model: str
    success: bool
    reason: str
    seconds: float
    llm_calls: int
    prompt_tokens: int
    cache_read_tokens: int
    completion_tokens: int
    cost_usd: float | None
    tool_calls: int
    tool_errors: int
    error: str | None = None


def _ensure_project_and_agent(owner: str, model: str) -> tuple[dict, dict]:
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config

    project = next((p for p in project_config.list_for_user(owner) if p.get("name") == BENCH_PROJECT_NAME), None)
    if project is None:
        project = project_config.create(BENCH_PROJECT_NAME, members=[owner], llm_model=model, created_by=owner,
                                        description="Fester Testsatz für Harness-Änderungen. Nicht für echte Arbeit.")
    agent = agent_config.get(project["agent_id"])
    changes = {"llm_model": model, "tools": BENCH_TOOLS, "fallback_models": [], "name": BENCH_AGENT_NAME}
    if any(agent.get(k) != v for k, v in changes.items()):
        agent = agent_config.update(agent["id"], **changes)
    return project, agent


def _metrics(session_id: str) -> dict:
    with db() as conn:
        llm = conn.execute(
            """SELECT COUNT(*) calls, COALESCE(SUM(prompt_tokens),0) prompt, COALESCE(SUM(cache_read_tokens),0) cache,
                      COALESCE(SUM(completion_tokens),0) completion, SUM(cost_micros) cost
               FROM llm_calls WHERE session_id = ?""", (session_id,),
        ).fetchone()
        tools = conn.execute(
            """SELECT COUNT(*) total, SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) errors
               FROM tool_calls WHERE session_id = ?""", (session_id,),
        ).fetchone()
    return {
        "llm_calls": llm["calls"], "prompt_tokens": llm["prompt"], "cache_read_tokens": llm["cache"],
        "completion_tokens": llm["completion"],
        "cost_usd": round(llm["cost"] / 1e6, 4) if llm["cost"] is not None else None,
        "tool_calls": tools["total"] or 0, "tool_errors": tools["errors"] or 0,
    }


async def _run_one(task: BenchTask, attempt: int, workspace: Path, project: dict, agent: dict,
                   owner: str) -> RunResult:
    from hydrahive.db import sessions as sessions_db
    from hydrahive.runner import run
    from hydrahive.runner.events import Done, Error, TextBlock, TextDelta

    task_dir = workspace / "bench" / f"{task.id}-{attempt}"
    if task_dir.exists():
        shutil.rmtree(task_dir)
    task_dir.mkdir(parents=True)
    task.setup(task_dir)

    session = sessions_db.create(agent["id"], owner, project_id=project["id"], title=f"bench {task.id} #{attempt}")
    prompt = f"Arbeitsordner für diese Aufgabe: {task_dir}\n\n{task.prompt}"
    answer, error = "", None
    started = time.monotonic()
    async for event in run(session.id, prompt):
        if isinstance(event, (TextDelta, TextBlock)):
            answer += event.text
        elif isinstance(event, Error):
            error = event.message
        elif isinstance(event, Done):
            break
    seconds = round(time.monotonic() - started, 1)
    try:
        success, reason = task.check(task_dir, answer)
    except Exception as exc:  # noqa: BLE001 – Prüfungsfehler zählt als nicht bestanden, nie als Absturz
        success, reason = False, f"Prüfung fehlgeschlagen: {exc}"
    return RunResult(task.id, attempt, agent["llm_model"], success and error is None, reason, seconds,
                     error=error, **_metrics(session.id))


async def run_bench(*, owner: str, model: str, attempts: int, only: list[str] | None = None) -> list[dict]:
    from hydrahive.projects._paths import workspace_path

    project, agent = _ensure_project_and_agent(owner, model)
    workspace = workspace_path(project["id"])
    tasks = [t for t in TASKS if not only or t.id in only]
    results = []
    for attempt in range(1, attempts + 1):
        for task in tasks:
            results.append(asdict(await _run_one(task, attempt, workspace, project, agent, owner)))
    return results
