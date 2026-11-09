"""Lokaler read-only Collector für den Harness Doctor."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from hydrahive.agents import config as agent_config
from hydrahive.db.connection import db
from hydrahive.plugins import tool_bridge as plugin_tools
from hydrahive.projects import config as project_config
from hydrahive.projects.execution import of as project_execution
from hydrahive.runner._project_tool_scope import scope_tools
from hydrahive.runner.integrity_metrics import summarize_integrity
from hydrahive.settings import settings
from hydrahive.skills.loader import list_for_agent
from hydrahive.tools import schemas_for
from hydrahive.harness_doctor.rules import evaluate


def _p90(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * .9))]


def _agent_metrics(agent: dict, projects: dict[str, dict]) -> dict[str, Any]:
    project_id = agent.get("project_id")
    project = projects.get(project_id) if project_id else None
    local_tools, mcp_servers = scope_tools(project, list(agent.get("tools") or []), list(agent.get("mcp_servers") or []))
    schemas = schemas_for(local_tools) + plugin_tools.schemas_for(local_tools)
    skills = list_for_agent(
        agent["id"], agent.get("owner"), disabled=agent.get("disabled_skills") or [], project_id=project_id,
    )
    return {
        "id": agent["id"], "name": agent.get("name") or agent["id"], "type": agent.get("type"),
        "project_id": project_id, "configured_tools": len(local_tools), "mcp_servers": len(mcp_servers),
        "tool_schemas": len(schemas), "tool_schema_chars": len(json.dumps(schemas, ensure_ascii=False)),
        "skill_metadata_chars": sum(len(s.name) + len(s.when_to_use or s.description or "") + 8 for s in skills),
        "skills": len(skills), "system_prompt_chars": len(agent_config.get_system_prompt(agent["id"])),
        "longterm_memory": bool(agent.get("longterm_memory")),
        "shell": "shell_exec" in local_tools,
        "require_tool_confirm": bool(agent.get("require_tool_confirm")),
        "execution_mode": project_execution(project).get("mode", "host") if project else "host",
    }


def _telemetry(hours: int) -> dict[str, Any]:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="milliseconds")
    with db() as conn:
        tools = dict(conn.execute(
            """SELECT COUNT(*) tool_calls,
                      SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) tool_errors,
                      SUM(CASE WHEN result_truncated = 1 THEN 1 ELSE 0 END) tool_truncated
               FROM tool_calls WHERE created_at >= ?""", (since,),
        ).fetchone())
        compactions = conn.execute(
            "SELECT duration_ms, error FROM compaction_events WHERE created_at >= ?", (since,),
        ).fetchall()
        delegations = conn.execute(
            """SELECT status, COUNT(*) amount FROM agent_delegations
               WHERE created_at >= ? AND status != 'running' GROUP BY status""", (since,),
        ).fetchall()
        task_columns = {row["name"] for row in conn.execute("PRAGMA table_info(module_tasks)").fetchall()}
    comp_durations = [int(row["duration_ms"] or 0) for row in compactions if not row["error"]]
    delegation_counts = {row["status"]: int(row["amount"]) for row in delegations}
    bad = sum(delegation_counts.get(status, 0) for status in ("error", "lost", "timeout"))
    return {
        "tool_calls": int(tools.get("tool_calls") or 0),
        "tool_errors": int(tools.get("tool_errors") or 0),
        "tool_truncated": int(tools.get("tool_truncated") or 0),
        "compactions": len(compactions),
        "compaction_errors": sum(1 for row in compactions if row["error"]),
        "compaction_p90_ms": _p90(comp_durations),
        "task_evidence_structured": {"objective", "acceptance_criteria", "evidence"} <= task_columns,
        "delegations_terminal": sum(delegation_counts.values()),
        "delegations_bad": bad,
        "delegation_statuses": delegation_counts,
    }


def run_doctor(hours: int) -> dict[str, Any]:
    agents = [agent for agent in agent_config.list_all() if agent.get("status") == "active"]
    project_list = [project for project in project_config.list_all() if project.get("status") == "active"]
    projects = {project["id"]: project for project in project_list}
    agent_rows = []
    for agent in agents:
        try:
            agent_rows.append(_agent_metrics(agent, projects))
        except Exception:
            agent_rows.append({
                "id": agent["id"], "name": agent.get("name") or agent["id"], "type": agent.get("type"),
                "project_id": agent.get("project_id"), "configured_tools": len(agent.get("tools") or []),
                "tool_schemas": 0, "tool_schema_chars": 0, "skill_metadata_chars": 0,
                "skills": 0, "system_prompt_chars": 0, "longterm_memory": bool(agent.get("longterm_memory")),
                "shell": "shell_exec" in (agent.get("tools") or []),
                "require_tool_confirm": bool(agent.get("require_tool_confirm")), "execution_mode": "unknown",
                "collection_error": True,
            })
    telemetry = _telemetry(hours)
    integrity = summarize_integrity(hours)
    complex_rows = [row for row in agent_rows if row.get("type") in ("master", "project")]
    shell_rows = [row for row in agent_rows if row.get("shell") and row.get("execution_mode") != "container"]
    mapped = sum(1 for project in project_list if any(
        row["id"] == project.get("agent_id") and row.get("type") == "project" for row in agent_rows
    ))
    workflow_dir = Path(settings.base_dir) / ".github" / "workflows"
    ci_workflows = len(list(workflow_dir.glob("*.yml"))) + len(list(workflow_dir.glob("*.yaml")))
    snapshot = {
        "max_tool_schema_chars": max((row["tool_schema_chars"] for row in agent_rows), default=0),
        "max_skill_metadata_chars": max((row["skill_metadata_chars"] for row in agent_rows), default=0),
        "max_system_prompt_chars": max((row["system_prompt_chars"] for row in agent_rows), default=0),
        "max_configured_tools": max((row["configured_tools"] for row in agent_rows), default=0),
        "collector_errors": sum(bool(row.get("collection_error")) for row in agent_rows),
        "shell_agents": len(shell_rows),
        "shell_confirm_disabled": sum(not row["require_tool_confirm"] for row in shell_rows),
        "complex_agents": len(complex_rows),
        "memory_agents": sum(row["longterm_memory"] for row in complex_rows),
        "completion_claims": integrity["completion_claims"],
        "unverified_claims": integrity["unverified_completion_claims"],
        "integrity_mode": getattr(settings, "integrity_mode", "observe"),
        "ci_workflows": ci_workflows,
        "active_projects": len(project_list),
        "mapped_project_agents": mapped,
        **telemetry,
    }
    scores = evaluate(snapshot)
    outliers = sorted(agent_rows, key=lambda row: row["tool_schema_chars"], reverse=True)[:10]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "window_hours": hours,
        **scores,
        "snapshot": snapshot,
        "agent_outliers": outliers,
        "notes": [
            "Tool-Schema-Größe umfasst lokale registrierte Schemas vor per-User Access-Filter.",
            "Scores sind deterministische Warnregeln, keine Kausalitäts- oder Qualitätsbeweise.",
        ],
    }
