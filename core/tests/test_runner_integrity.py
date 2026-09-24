from hydrahive.runner.integrity import IntegrityState, canonical_tool_payload
from hydrahive.tools.base import ToolResult


def test_canonical_tool_payload_ignores_only_ephemeral_fields():
    first = canonical_tool_payload("shell_exec", {"cmd": "echo hi", "request_id": "one"})
    second = canonical_tool_payload("shell_exec", {"cmd": "echo hi", "request_id": "two"})
    changed = canonical_tool_payload("shell_exec", {"cmd": "echo bye", "request_id": "two"})

    assert first == second
    assert first != changed
    assert "echo hi" in first
    assert "one" not in first


def test_repeated_action_signal_is_bounded_and_does_not_store_arguments():
    state = IntegrityState(goal="prüfe den Fix")
    signals = []
    for _ in range(4):
        signals.extend(state.record_tool("shell_exec", {"cmd": "echo hi"}, ToolResult.ok("same")))

    assert any(signal.kind == "repeated_tool_action" for signal in signals)
    snapshot = state.snapshot()
    assert snapshot["tool_observations"] == 4
    assert snapshot["unique_actions"] == 1
    assert "echo hi" not in repr(snapshot)


def test_error_chain_and_no_progress_are_detected():
    state = IntegrityState(goal="behebe den Fehler")
    signals = []
    for _ in range(3):
        signals.extend(state.record_tool("fetch_url", {"url": "https://example.test"}, ToolResult.fail("timeout")))

    kinds = {signal.kind for signal in signals}
    assert "error_chain" in kinds
    assert "no_progress" in kinds


def test_new_successful_evidence_resets_no_progress_streak():
    state = IntegrityState(goal="prüfe zwei Zustände")
    for _ in range(2):
        state.record_tool("shell_exec", {"cmd": "echo same"}, ToolResult.ok("same"))

    signals = state.record_tool("shell_exec", {"cmd": "echo new"}, ToolResult.ok("new"))

    assert not any(signal.kind == "no_progress" for signal in signals)
    assert state.snapshot()["new_evidence"] == 2


def test_completion_claims_are_telemetried_without_claim_text():
    state = IntegrityState(goal="ändere und teste")
    signals = state.record_assistant_text("Der Fix ist implementiert und erfolgreich getestet.")

    assert any(signal.kind == "completion_claim" for signal in signals)
    snapshot = state.snapshot()
    assert snapshot["completion_claims"] == 2
    assert "implementiert" not in repr(snapshot)


def test_assistant_blocks_only_inspects_visible_text():
    state = IntegrityState(goal="prüfe den Lauf")
    signals = state.record_assistant_blocks([
        {"type": "text", "text": "Der Fix ist getestet."},
        {"type": "tool_use", "name": "shell_exec", "input": {"cmd": "echo deployed"}},
    ])

    assert [signal.kind for signal in signals] == ["completion_claim"]
    assert state.snapshot()["completion_claim_kinds"] == ["tested"]


def test_drain_signals_is_bounded_and_consumes_pending_signals():
    state = IntegrityState(goal="prüfe den Lauf")
    for _ in range(4):
        state.record_tool("shell_exec", {"cmd": "echo hi"}, ToolResult.ok("same"))

    pending = state.drain_signals()

    assert {signal["kind"] for signal in pending} == {"repeated_tool_action", "no_progress"}
    assert state.drain_signals() == []
    assert all(set(signal) == {"kind", "level", "detail"} for signal in pending)


def test_negated_completion_is_not_counted_as_claim():
    state = IntegrityState(goal="ändere und teste")

    signals = state.record_assistant_text(
        "Der Fix ist noch nicht implementiert und wurde nicht erfolgreich getestet."
    )

    assert signals == []
    assert state.snapshot()["completion_claims"] == 0


def test_raw_secrets_never_appear_in_integrity_metadata():
    secret = "sk-live-super-secret-value"
    state = IntegrityState(goal=f"Prüfe {secret}")

    state.record_tool(
        "fetch_url", {"headers": {"Authorization": f"Bearer {secret}"}},
        ToolResult.ok({"token": secret}),
    )

    assert secret not in repr(state.audit_metadata())
