from hydrahive.llm.reasoning_effort import effort_levels_for_model
from hydrahive.runner._codex_provider import _build_payload


def test_gpt54_and_55_support_low_through_xhigh():
    expected = ("low", "medium", "high", "xhigh")
    assert effort_levels_for_model("openai-codex/gpt-5.4") == expected
    assert effort_levels_for_model("openai-codex/gpt-5.5") == expected


def test_gpt56_luna_supports_max_not_ultra():
    assert effort_levels_for_model("openai-codex/gpt-5.6-luna") == (
        "low", "medium", "high", "xhigh", "max",
    )


def test_gpt56_sol_and_terra_support_ultra():
    expected = ("low", "medium", "high", "xhigh", "max", "ultra")
    assert effort_levels_for_model("openai-codex/gpt-5.6-sol") == expected
    assert effort_levels_for_model("openai-codex/gpt-5.6-terra") == expected


def test_codex_payload_contains_selected_effort():
    payload = _build_payload(
        model="gpt-5.4", system_prompt="", messages=[], tools=[], reasoning_effort="high",
    )
    assert payload["reasoning"] == {"effort": "high"}


def test_codex_payload_ignores_unsupported_effort():
    payload = _build_payload(
        model="gpt-5.6-luna", system_prompt="", messages=[], tools=[], reasoning_effort="ultra",
    )
    assert "reasoning" not in payload
