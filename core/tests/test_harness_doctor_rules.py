from hydrahive.harness_doctor.rules import evaluate


def _healthy() -> dict:
    return {
        "max_tool_schema_chars": 20_000,
        "max_skill_metadata_chars": 5_000,
        "max_system_prompt_chars": 8_000,
        "max_configured_tools": 40,
        "collector_errors": 0,
        "shell_agents": 0,
        "shell_confirm_disabled": 0,
        "tool_calls": 100,
        "tool_errors": 0,
        "tool_truncated": 0,
        "compactions": 20,
        "compaction_errors": 0,
        "compaction_p90_ms": 100_000,
        "complex_agents": 10,
        "memory_agents": 10,
        "task_evidence_structured": True,
        "completion_claims": 100,
        "unverified_claims": 0,
        "ci_workflows": 2,
        "active_projects": 5,
        "mapped_project_agents": 5,
        "delegations_terminal": 20,
        "delegations_bad": 0,
    }


def test_healthy_snapshot_scores_100():
    result = evaluate(_healthy())
    assert result["overall_score"] == 100
    assert all(item["score"] == 100 for item in result["dimensions"])
    assert result["priorities"] == []


def test_known_gaps_are_deterministic_and_traceable():
    snapshot = _healthy() | {
        "max_tool_schema_chars": 70_000,
        "shell_agents": 4,
        "shell_confirm_disabled": 4,
        "compactions": 10,
        "compaction_errors": 2,
        "compaction_p90_ms": 700_000,
        "completion_claims": 100,
        "unverified_claims": 8,
        "delegations_terminal": 20,
        "delegations_bad": 6,
    }
    result = evaluate(snapshot)
    ids = {finding["rule_id"] for dim in result["dimensions"] for finding in dim["findings"]}
    assert {"instructions.schema_size", "tools.host_shell", "state.compaction_errors",
            "verification.unverified", "lifecycle.delegations"} <= ids
    assert all({"rule_id", "actual", "target", "deduction", "source"} <= finding.keys()
               for dim in result["dimensions"] for finding in dim["findings"])
    assert 0 <= result["overall_score"] < 100
    assert 1 <= len(result["priorities"]) <= 3


def test_empty_windows_do_not_create_fake_rates():
    snapshot = _healthy() | {"tool_calls": 0, "compactions": 0, "completion_claims": 0,
                             "delegations_terminal": 0}
    result = evaluate(snapshot)
    ids = {finding["rule_id"] for dim in result["dimensions"] for finding in dim["findings"]}
    assert "tools.error_rate" not in ids
    assert "state.compaction_errors" not in ids
    assert "verification.unverified" not in ids
    assert "lifecycle.delegations" not in ids


def test_keine_regel_ohne_echte_datenquelle():
    """Review 09.11.2026: eine Regel las eine nicht existierende Einstellung und zog immer 15 Punkte ab."""
    result = evaluate(_healthy())
    ids = {f["rule_id"] for d in result["dimensions"] for f in d["findings"]}
    assert "verification.integrity_mode" not in ids
