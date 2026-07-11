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


def test_codex_payload_sets_output_limit():
    payload = _build_payload(
        model="gpt-5.6-sol", system_prompt="", messages=[], tools=[], max_tokens=32_000,
    )
    assert payload["max_output_tokens"] == 32_000


def test_encrypted_reasoning_replayed_for_same_model_only():
    messages = [{"role": "assistant", "content": [
        {"type": "codex_reasoning", "encrypted_content": "opaque", "model": "openai-codex/gpt-5.6-sol"},
        {"type": "text", "text": "done"},
    ]}]
    _, same = messages_to_codex(messages, model="openai-codex/gpt-5.6-sol")
    _, switched = messages_to_codex(messages, model="openai-codex/gpt-5.5")
    assert {"type": "reasoning", "encrypted_content": "opaque"} in same
    assert all(item.get("type") != "reasoning" for item in switched)


def test_codex_payload_requests_cache_replay_material():
    payload = _build_payload(model="gpt-5.5", system_prompt="", messages=[], tools=[])
    assert "reasoning.encrypted_content" in payload["include"]
