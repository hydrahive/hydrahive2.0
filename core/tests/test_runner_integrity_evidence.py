from hydrahive.runner.integrity import IntegrityState
from hydrahive.runner.integrity_evidence import evidence_for_tool
from hydrahive.tools.base import ToolResult


def test_file_patch_provides_artifact_change_evidence():
    evidence = evidence_for_tool("file_patch", {"path": "a.py"}, succeeded=True)

    assert evidence == {"artifact_changed"}


def test_successful_pytest_command_provides_test_evidence():
    evidence = evidence_for_tool(
        "shell_exec", {"cmd": "cd core && pytest -q"}, succeeded=True,
    )

    assert evidence == {"tests_passed"}


def test_common_test_runners_are_recognized():
    commands = [
        "python -m pytest tests/test_x.py",
        "go test ./...",
        "cargo test",
        "npm test",
        "pnpm run test",
        "yarn test",
    ]

    for command in commands:
        assert evidence_for_tool("shell_exec", {"cmd": command}, succeeded=True) == {"tests_passed"}


def test_failed_or_masked_test_command_provides_no_evidence():
    commands = [
        "pytest -q || true",
        "pytest -q | tail -20",
        "pytest -q; echo finished",
        "set +e\npytest -q",
        "pytest --collect-only",
        "pytest --help",
        "python -m pytest --version",
    ]

    for command in commands:
        assert evidence_for_tool("shell_exec", {"cmd": command}, succeeded=True) == set()
    assert evidence_for_tool("shell_exec", {"cmd": "pytest -q"}, succeeded=False) == set()


def test_implemented_claim_is_supported_by_prior_file_change():
    state = IntegrityState(goal="ändere die Datei")
    state.record_tool("file_patch", {"path": "a.py"}, ToolResult.ok("patched"))
    state.drain_signals()

    signals = state.record_assistant_text("Der Fix ist implementiert.")

    assert "unverified_completion_claim" not in {signal.kind for signal in signals}
    assert state.snapshot()["evidence_kinds"] == ["artifact_changed"]


def test_tested_claim_without_test_evidence_is_marked_unverified():
    state = IntegrityState(goal="ändere die Datei")
    state.record_tool("file_patch", {"path": "a.py"}, ToolResult.ok("patched"))
    state.drain_signals()

    signals = state.record_assistant_text("Der Fix ist getestet.")

    kinds = [signal.kind for signal in signals]
    assert kinds == ["completion_claim", "unverified_completion_claim"]
    assert "tests_passed" in signals[-1].detail


def test_fixed_claim_requires_change_and_test_evidence():
    state = IntegrityState(goal="behebe den Fehler")
    state.record_tool("file_patch", {"path": "a.py"}, ToolResult.ok("patched"))
    state.record_tool(
        "shell_exec", {"cmd": "pytest -q"},
        ToolResult.ok({"exit_code": 0, "stdout": "5 passed", "stderr": ""}, exit_code=0),
    )
    state.drain_signals()

    signals = state.record_assistant_text("Der Fehler ist behoben.")

    assert "unverified_completion_claim" not in {signal.kind for signal in signals}
    assert state.snapshot()["evidence_kinds"] == ["artifact_changed", "tests_passed"]


def test_evidence_snapshot_never_contains_raw_command_or_output():
    secret = "private-command-value"
    state = IntegrityState(goal="prüfe")
    state.record_tool(
        "shell_exec", {"cmd": f"pytest -q --token={secret}"},
        ToolResult.ok({"exit_code": 0, "stdout": secret, "stderr": ""}, exit_code=0),
    )

    assert secret not in repr(state.audit_metadata())
