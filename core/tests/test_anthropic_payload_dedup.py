"""Dedup der Anthropic-Payload-Helfer + Fix der _block_to_dict-Drift (#200).

Der Streaming-Pfad fiel bei SDK-Objekten ohne model_dump auf einen verlust-
behafteten {"type": ...}-Stub zurück, der Non-Stream-Pfad serialisierte voll.
Jetzt teilen sich beide das kanonische block_to_dict (mit .dict()+JSON-Fallback).
"""
from __future__ import annotations


class _ModelDumpBlock:
    def model_dump(self):
        return {"type": "text", "text": "hi"}


class _DictBlock:
    def dict(self):
        return {"type": "thinking", "thinking": "deep"}


class _LegacyBlock:
    """Weder model_dump noch dict — nur Attribute (z.B. alter ThinkingBlock)."""
    def __init__(self):
        self.type = "thinking"
        self.thinking = "important reasoning"


def test_block_to_dict_uses_model_dump():
    from hydrahive.runner._anthropic_payload import block_to_dict
    assert block_to_dict(_ModelDumpBlock()) == {"type": "text", "text": "hi"}


def test_block_to_dict_uses_dict_method():
    from hydrahive.runner._anthropic_payload import block_to_dict
    assert block_to_dict(_DictBlock()) == {"type": "thinking", "thinking": "deep"}


def test_block_to_dict_passes_through_plain_dict():
    from hydrahive.runner._anthropic_payload import block_to_dict
    assert block_to_dict({"type": "tool_use", "id": "x"}) == {"type": "tool_use", "id": "x"}


def test_block_to_dict_json_fallback_preserves_data():
    from hydrahive.runner._anthropic_payload import block_to_dict
    out = block_to_dict(_LegacyBlock())
    # Kein verlustbehafteter Stub mehr — der Inhalt bleibt erhalten.
    assert out.get("type") == "thinking"
    assert out.get("thinking") == "important reasoning"


def test_stream_and_backend_share_canonical_block_to_dict():
    from hydrahive.runner import _anthropic_payload
    from hydrahive.runner import _stream_providers, _llm_bridge_backends
    assert _stream_providers._block_to_dict is _anthropic_payload.block_to_dict
    assert _llm_bridge_backends._block_to_dict is _anthropic_payload.block_to_dict
    # Der frühere Stream-Bug: Legacy-Block verlor seine Daten.
    assert _stream_providers._block_to_dict(_LegacyBlock()).get("thinking") == "important reasoning"


def test_stream_usage_dict_is_canonical():
    from hydrahive.runner import _stream_providers
    from hydrahive.runner._token_usage import usage_dict
    assert _stream_providers.usage_dict is usage_dict
    assert not hasattr(_stream_providers, "_usage_dict")
