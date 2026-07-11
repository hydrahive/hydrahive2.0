from hydrahive.llm.reasoning_effort import effort_levels_for_model
from hydrahive.runner._codex_provider import _build_payload


def test_gpt54_supports_none_through_xhigh_not_max():
    levels = effort_levels_for_model("openai-codex/gpt-5.4")
    assert levels == ("none", "low", "medium", "high", "xhigh")


def test_gpt56_supports_max():
    assert effort_levels_for_model("openai-codex/gpt-5.6-sol")[-1] == "max"


def test_legacy_codex_supports_minimal_not_xhigh():
    assert effort_levels_for_model("openai-codex/gpt-5.1-codex-max") == (
        "minimal", "low", "medium", "high",
    )


def test_codex_payload_contains_selected_effort():
    payload = _build_payload(
        model="gpt-5.4", system_prompt="", messages=[], tools=[], reasoning_effort="high",
    )
    assert payload["reasoning"] == {"effort": "high"}


def test_codex_payload_ignores_unsupported_effort():
    payload = _build_payload(
        model="gpt-5.4", system_prompt="", messages=[], tools=[], reasoning_effort="max",
    )
    assert "reasoning" not in payload
