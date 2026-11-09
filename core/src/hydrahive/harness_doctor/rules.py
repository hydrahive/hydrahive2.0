"""Deterministische, transparente Regeln des read-only Harness Doctors."""
from __future__ import annotations

from typing import Any

_DIMENSIONS = (
    ("instructions", "Instructions"),
    ("tools", "Tools / Environment"),
    ("state", "State"),
    ("verification", "Verification"),
    ("lifecycle", "Scope / Lifecycle"),
)


def _finding(rule_id: str, title: str, actual: Any, target: str, deduction: int,
             source: str, recommendation: str) -> dict[str, Any]:
    severity = "critical" if deduction >= 20 else "warning" if deduction >= 10 else "info"
    return {"rule_id": rule_id, "title": title, "actual": actual, "target": target,
            "deduction": deduction, "severity": severity, "source": source,
            "recommendation": recommendation}


def _rate(part: int, total: int) -> float | None:
    return part / total if total else None


def evaluate(snapshot: dict[str, Any]) -> dict[str, Any]:
    findings: dict[str, list[dict[str, Any]]] = {key: [] for key, _ in _DIMENSIONS}

    def add(dim: str, *args: Any) -> None:
        findings[dim].append(_finding(*args))

    if snapshot["collector_errors"]:
        add("instructions", "instructions.collection_errors", "Agent-Metriken unvollständig",
            snapshot["collector_errors"], "0", 20, "Harness-Collector",
            "Collector-Fehler beheben; fehlende Werte nie als gesund werten.")
    schemas = snapshot["max_tool_schema_chars"]
    if schemas > 60_000:
        add("instructions", "instructions.schema_size", "Sehr große Tool-Schema-Fläche", schemas, "≤ 30.000 Zeichen", 25,
            "lokale Tool-Registry", "Werkzeuggruppen aufgabenbezogen per JIT laden.")
    elif schemas > 40_000:
        add("instructions", "instructions.schema_size", "Große Tool-Schema-Fläche", schemas, "≤ 30.000 Zeichen", 15,
            "lokale Tool-Registry", "Werkzeuggruppen enger schneiden.")
    elif schemas > 25_000:
        add("instructions", "instructions.schema_size", "Tool-Schema-Fläche beobachten", schemas, "≤ 25.000 Zeichen", 5,
            "lokale Tool-Registry", "Schemawachstum messen.")
    if snapshot["max_skill_metadata_chars"] > 10_000:
        add("instructions", "instructions.skill_metadata", "Viele Skill-Metadaten", snapshot["max_skill_metadata_chars"],
            "≤ 10.000 Zeichen", 10, "Skill-Loader", "Skill-Metadaten konsolidieren; Bodies weiter JIT laden.")
    if snapshot["max_system_prompt_chars"] > 20_000:
        add("instructions", "instructions.system_prompt", "Sehr großer Basis-Systemprompt", snapshot["max_system_prompt_chars"],
            "≤ 10.000 Zeichen", 15, "Agent-Konfiguration", "Stabile Regeln kürzen oder in Skills auslagern.")
    elif snapshot["max_system_prompt_chars"] > 10_000:
        add("instructions", "instructions.system_prompt", "Großer Basis-Systemprompt", snapshot["max_system_prompt_chars"],
            "≤ 10.000 Zeichen", 5, "Agent-Konfiguration", "Prompt auf Dopplungen prüfen.")
    if snapshot["max_configured_tools"] > 120:
        add("instructions", "instructions.tool_count", "Sehr breite Toolkonfiguration", snapshot["max_configured_tools"],
            "≤ 80 Tools", 15, "Agent-Konfiguration", "Breite Agenten in Intent-Gruppen aufteilen.")
    elif snapshot["max_configured_tools"] > 80:
        add("instructions", "instructions.tool_count", "Breite Toolkonfiguration", snapshot["max_configured_tools"],
            "≤ 80 Tools", 8, "Agent-Konfiguration", "Nur benötigte Werkzeuge konfigurieren.")

    if snapshot["shell_agents"]:
        add("tools", "tools.host_shell", "Agenten mit Host-Shell", snapshot["shell_agents"], "0 ohne Container-Isolation", 20,
            "Agent-/Projektkonfiguration", "Shell-Isolationstask priorisieren.")
    if snapshot["shell_confirm_disabled"]:
        add("tools", "tools.confirmation", "Shell-Agenten ohne globales Confirm-Flag", snapshot["shell_confirm_disabled"],
            "0", 10, "Agent-Konfiguration", "Delegationsfeste High-Risk-Gates prüfen.")
    trunc = _rate(snapshot["tool_truncated"], snapshot["tool_calls"])
    if trunc is not None and trunc > .05:
        add("tools", "tools.truncation_rate", "Hohe Tool-Trunkierungsrate", round(trunc, 4), "≤ 1 %", 15,
            "tool_calls", "Große Listen serverseitig paginieren.")
    elif trunc is not None and trunc > .01:
        add("tools", "tools.truncation_rate", "Tool-Trunkierung beobachten", round(trunc, 4), "≤ 1 %", 7,
            "tool_calls", "Top-Verursacher nach Ergebnisbytes prüfen.")
    tool_errors = _rate(snapshot["tool_errors"], snapshot["tool_calls"])
    if tool_errors is not None and tool_errors > .10:
        add("tools", "tools.error_rate", "Hohe Tool-Fehlerrate", round(tool_errors, 4), "≤ 3 %", 15,
            "tool_calls", "Fehler nach Tool und Ursache priorisieren.")
    elif tool_errors is not None and tool_errors > .03:
        add("tools", "tools.error_rate", "Tool-Fehlerrate erhöht", round(tool_errors, 4), "≤ 3 %", 7,
            "tool_calls", "Fehlercluster prüfen.")

    comp_errors = _rate(snapshot["compaction_errors"], snapshot["compactions"])
    if comp_errors is not None and comp_errors > .10:
        add("state", "state.compaction_errors", "Hohe Compaction-Fehlerrate", round(comp_errors, 4), "≤ 3 %", 25,
            "compaction_events", "Fallback, Cooldown und Fehlercluster prüfen.")
    elif comp_errors is not None and comp_errors > .03:
        add("state", "state.compaction_errors", "Compaction-Fehlerrate erhöht", round(comp_errors, 4), "≤ 3 %", 10,
            "compaction_events", "Fehlercluster beobachten.")
    if snapshot["compaction_p90_ms"] > 900_000:
        add("state", "state.compaction_duration", "Compaction p90 über Zeitbudget", snapshot["compaction_p90_ms"],
            "≤ 900.000 ms", 15, "compaction_events", "Chunkanzahl und Modelllaufzeit untersuchen.")
    elif snapshot["compaction_p90_ms"] > 300_000:
        add("state", "state.compaction_duration", "Compaction p90 langsam", snapshot["compaction_p90_ms"],
            "≤ 300.000 ms", 10, "compaction_events", "Chunk-Packing und Modellwahl messen.")
    memory_rate = _rate(snapshot["memory_agents"], snapshot["complex_agents"])
    if memory_rate is not None and memory_rate < .5:
        add("state", "state.memory_coverage", "Geringe Memory-Abdeckung", round(memory_rate, 4), "≥ 80 %", 15,
            "Agent-Konfiguration", "Memory für langlebige Master-/Projektagenten prüfen.")
    elif memory_rate is not None and memory_rate < .8:
        add("state", "state.memory_coverage", "Memory-Abdeckung unvollständig", round(memory_rate, 4), "≥ 80 %", 7,
            "Agent-Konfiguration", "Fehlende langlebige Agenten prüfen.")
    if not snapshot["task_evidence_structured"]:
        add("state", "state.task_evidence", "Keine strukturierten Task-Evidenzfelder", False, "vorhanden", 15,
            "module_tasks-Schema", "Ziel, Akzeptanzkriterien und Evidenz strukturiert speichern.")

    unverified = _rate(snapshot["unverified_claims"], snapshot["completion_claims"])
    if unverified is not None and unverified > .05:
        add("verification", "verification.unverified", "Hohe Rate unbelegter Abschlussclaims", round(unverified, 4),
            "≤ 1 %", 25, "Integrity-Metadaten", "Abschlussclaims an frische Evidenz koppeln.")
    elif unverified is not None and unverified > .01:
        add("verification", "verification.unverified", "Unbelegte Abschlussclaims vorhanden", round(unverified, 4),
            "≤ 1 %", 10, "Integrity-Metadaten", "Evidenz-Gate pilotieren.")
    if snapshot["ci_workflows"] < 2:
        add("verification", "verification.ci", "Zu wenige erkannte CI-Workflows", snapshot["ci_workflows"], "≥ 2", 20,
            ".github/workflows", "Backend-, Frontend- und Spec-Prüfungen sicherstellen.")

    project_rate = _rate(snapshot["mapped_project_agents"], snapshot["active_projects"])
    if project_rate is not None and project_rate < 1:
        add("lifecycle", "lifecycle.project_agents", "Aktive Projekte ohne gültigen Projektagenten", round(project_rate, 4),
            "100 %", 15, "Projektkonfiguration", "Projekt-Agent-Zuordnung reparieren.")
    bad_delegations = _rate(snapshot["delegations_bad"], snapshot["delegations_terminal"])
    if bad_delegations is not None and bad_delegations > .25:
        add("lifecycle", "lifecycle.delegations", "Hohe terminale Delegationsfehlerrate", round(bad_delegations, 4),
            "≤ 10 %", 25, "agent_delegations", "Lost/Timeout/Error getrennt messen und beheben.")
    elif bad_delegations is not None and bad_delegations > .10:
        add("lifecycle", "lifecycle.delegations", "Delegationsfehlerrate erhöht", round(bad_delegations, 4),
            "≤ 10 %", 10, "agent_delegations", "Terminalen Fachstatus vom Tool-Ack trennen.")

    dimensions = []
    all_findings = []
    for key, label in _DIMENSIONS:
        score = max(0, 100 - sum(item["deduction"] for item in findings[key]))
        dimensions.append({"id": key, "label": label, "score": score, "findings": findings[key]})
        all_findings.extend(findings[key])
    overall = round(sum(item["score"] for item in dimensions) / len(dimensions))
    lowest = min(dimensions, key=lambda item: item["score"])
    priorities = sorted(all_findings, key=lambda item: (-item["deduction"], item["rule_id"]))[:3]
    return {"overall_score": overall, "lowest_dimension": lowest["id"],
            "dimensions": dimensions, "priorities": priorities}
