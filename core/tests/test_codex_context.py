from hydrahive.compaction.tokens import context_window_for
from hydrahive.runner._codex_convert import messages_to_codex
from hydrahive.runner._codex_provider import _build_payload


def test_codex_oauth_context_windows_match_official_client():
    assert context_window_for("openai-codex/gpt-5.6-sol") == 372_000
    assert context_window_for("openai-codex/gpt-5.6-terra") == 372_000
    assert context_window_for("openai-codex/gpt-5.6-luna") == 372_000
    assert context_window_for("openai-codex/gpt-5.5") == 272_000
    assert context_window_for("openai-codex/gpt-5.4") == 272_000
    assert context_window_for("openai-codex/gpt-5.4-mini") == 272_000


def test_codex_payload_omits_unsupported_output_limit():
    # Der Codex-OAuth-Endpunkt lehnt max_output_tokens mit HTTP 400 ab.
    payload = _build_payload(
        model="gpt-5.6-sol", system_prompt="", messages=[], tools=[], max_tokens=32_000,
    )
    assert "max_output_tokens" not in payload


def test_encrypted_reasoning_replayed_for_same_model_only():
    messages = [{"role": "assistant", "content": [
        {"type": "codex_reasoning", "encrypted_content": "opaque", "model": "openai-codex/gpt-5.6-sol"},
        {"type": "text", "text": "done"},
    ]}]
    _, same = messages_to_codex(messages, model="openai-codex/gpt-5.6-sol")
    _, switched = messages_to_codex(messages, model="openai-codex/gpt-5.5")
    assert {"type": "reasoning", "encrypted_content": "opaque", "summary": []} in same
    assert all(item.get("type") != "reasoning" for item in switched)


def test_replayed_reasoning_item_carries_summary_field():
    """Regression: Die Responses-API lehnt zurückgesendete reasoning-Items ohne
    'summary' mit HTTP 400 ab ("Missing required parameter: input[..].summary").
    Das ließ Codex-Modelle nach dem ERSTEN Tool-Call stumm abbrechen."""
    messages = [{"role": "assistant", "content": [
        {"type": "codex_reasoning", "encrypted_content": "enc", "model": "openai-codex/gpt-5.6-sol"},
        {"type": "tool_use", "id": "call_1", "name": "load_skill", "input": {"name": "x"}},
    ]}]
    _, items = messages_to_codex(messages, model="openai-codex/gpt-5.6-sol")
    reasoning = [i for i in items if i.get("type") == "reasoning"]
    assert reasoning and all("summary" in i for i in reasoning)


def test_codex_payload_requests_cache_replay_material():
    payload = _build_payload(model="gpt-5.5", system_prompt="", messages=[], tools=[])
    assert "reasoning.encrypted_content" in payload["include"]
