from hydrahive.agentlink.protocol import State, TaskBlock, WorkingMemory
from hydrahive.tools.ask_agent import _result_from_response


def _response(status: str, description: str, findings=()):
    return State(
        agent_id="hydrahive",
        task=TaskBlock(
            type="review", description=description, status=status,
        ),
        working_memory=WorkingMemory(findings=list(findings)),
    )


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
