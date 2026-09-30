"""Task 48278afd: adaptive thinking + temperature≠1 → Anthropic 400.

Belegt 29.09.2026: Spezialist faktenpruefer (claude-sonnet-5, temperature 0.7,
reasoning_effort high) bekam „`temperature` may only be set to 1 when thinking
is enabled or in adaptive mode“. Geprüft wird hier der echte Payload-Weg des
Runners (build_anthropic_kwargs), nicht nur apply_effort.
"""
from __future__ import annotations

import pytest

from hydrahive.runner._anthropic_payload import build_anthropic_kwargs


def _kwargs(model: str, effort: str | None, temperature: float = 0.7) -> dict:
    _, kwargs = build_anthropic_kwargs(
        key="sk-ant-api03-test", model=model, system_prompt="sys", volatile_system=None,
        summary_system=None, cache_ttl="5m", messages=[{"role": "user", "content": "hi"}],
        tools=[], temperature=temperature, max_tokens=4096, reasoning_effort=effort,
    )
    return kwargs


def test_faktenpruefer_config_sends_temperature_1():
    kw = _kwargs("claude-sonnet-5", "high", temperature=0.7)
    assert kw["thinking"] == {"type": "adaptive"}
    assert kw["temperature"] == 1.0


@pytest.mark.parametrize("model", ["claude-opus-5", "claude-opus-4-8", "claude-sonnet-4-6", "anthropic/claude-sonnet-5"])
def test_all_adaptive_models_send_temperature_1(model):
    assert _kwargs(model, "medium")["temperature"] == 1.0


def test_without_effort_temperature_unchanged():
    kw = _kwargs("claude-sonnet-5", None, temperature=0.7)
    assert kw["temperature"] == 0.7 and "thinking" not in kw


def test_legacy_model_still_temperature_1():
    kw = _kwargs("claude-opus-4-5", "high", temperature=0.7)
    assert kw["thinking"]["type"] == "enabled" and kw["temperature"] == 1.0
