from hydrahive.agentlink.protocol import State, TaskBlock, WorkingMemory
from hydrahive.tools.ask_agent import (
    _caller_agentlink_id,
    _response_timeout,
    _result_from_response,
)


def _response(status: str, description: str, findings=()):
    return State(
        agent_id="hydrahive",
        task=TaskBlock(
            type="review", description=description, status=status,
        ),
        working_memory=WorkingMemory(findings=list(findings)),
    )


def test_caller_identity_uses_immutable_local_agent_id(monkeypatch):
    monkeypatch.setattr(
        "hydrahive.tools.ask_agent.settings.agentlink_agent_id", "hydrahive",
        raising=False,
    )

    assert _caller_agentlink_id("uuid-project-a") == "hydrahive/uuid-project-a"
    assert _caller_agentlink_id("uuid-project-b") == "hydrahive/uuid-project-b"
    assert _caller_agentlink_id("") == "hydrahive"


def test_caller_timeout_outlives_configured_target_timeout(monkeypatch):
    monkeypatch.setattr(
        "hydrahive.tools.ask_agent.settings.agentlink_handoff_timeout", 600,
        raising=False,
    )
    monkeypatch.setattr(
        "hydrahive.tools.ask_agent.settings.agentlink_run_timeout", 540,
        raising=False,
    )

    target = {
        "handoff_timeout_seconds": 1_200,
        "max_iterations": 120,
        "max_tokens": 64_000,
    }
    assert _response_timeout(target, "deep") == 1_260
    assert _response_timeout(target, "standard") == 600
    assert _response_timeout(target, "quick") == 240
    assert _response_timeout(None, "deep") == 600


def test_checkpoint_reply_exposes_structured_resume_metadata():
    checkpoint = (
        'HH_CHECKPOINT_V1:{"version":1,"reason":"max_iterations",'
        '"resume_token":"handoff_12345678","session_id":"sess-1",'
        '"remaining_work":"Auftrag abschliessen und verifizieren"}'
    )
    result = _result_from_response(_response(
        "blocked", "Pausiert: Iterationslimit erreicht", ["Teilergebnis", checkpoint],
    ))

    assert not result.success
    assert result.metadata["checkpoint"]["resume_token"] == "handoff_12345678"
    assert "resume_token=\"handoff_12345678\"" in result.error
    assert "Teilergebnis" in result.error
    assert "HH_CHECKPOINT" not in result.error


def test_blocked_specialist_reply_is_tool_failure_with_partial_findings():
    result = _result_from_response(_response(
        "blocked", "Fehler: Max-Iterationen erreicht",
        ["Bisher wurden drei Dateien geprüft."],
    ))

    assert result.success is False
    assert "Max-Iterationen" in result.error
    assert "drei Dateien" in result.error


def test_done_specialist_reply_is_tool_success():
    result = _result_from_response(_response(
        "done", "Abgeschlossen: Review", ["Keine Findings."],
    ))

    assert result.success is True
    assert "Abgeschlossen" in result.output
    assert "Keine Findings" in result.output


def test_non_terminal_specialist_reply_is_not_treated_as_success():
    result = _result_from_response(_response("in_progress", "Noch in Arbeit"))

    assert result.success is False
    assert "in_progress" in result.error
