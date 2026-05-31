from __future__ import annotations

from hydrahive.llm import catalog


_OPENROUTER_RESPONSE = {
    "data": [
        {"id": "meta-llama/llama-3.3-70b-instruct:free",
         "context_length": 131072,
         "pricing": {"prompt": "0", "completion": "0"}},
        {"id": "anthropic/claude-sonnet-4-6",
         "context_length": 200000,
         "pricing": {"prompt": "0.000003", "completion": "0.000015"}},
    ]
}


def test_parse_models_marks_free_and_paid():
    entries = catalog._parse_models_response("openrouter", _OPENROUTER_RESPONSE)
    by_id = {e["id"]: e for e in entries}
    free = by_id["openrouter/meta-llama/llama-3.3-70b-instruct:free"]
    paid = by_id["openrouter/anthropic/claude-sonnet-4-6"]
    assert free["is_free"] is True
    assert free["context_window"] == 131072
    assert paid["is_free"] is False
    assert paid["price_prompt"] == "0.000003"


def test_parse_models_without_pricing_is_free_none():
    entries = catalog._parse_models_response("openai", {"data": [{"id": "gpt-4o"}]})
    assert entries[0]["id"] == "openai/gpt-4o"
    assert entries[0]["is_free"] is None
    assert entries[0]["context_window"] is None
