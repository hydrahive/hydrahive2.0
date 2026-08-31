"""Regression: Ollama-Modelle bekamen num_ctx=8192 (Default) statt ihres
echten Kontextfensters, weil context_window_for() nur die statische
METADATA-Tabelle kannte — die enthält keine Ollama-Modelle. Die echte,
live per /api/show geholte Kontextgröße steht bereits im Registry-Cache
(llm/registry.py, ModelEntry.context_window). Bug live gefunden von till:
ollama/gemma4:latest (echtes Fenster 131072) bekam num_ctx=8192, wodurch
das Modell bei einem vollen Agent-Kontext (~4k Token System-Prompt + Tools)
kaum noch Platz zum Antworten hatte -> Tool-Calling brach zuverlässig.
"""
from __future__ import annotations

from hydrahive.compaction.tokens import context_window_for
from hydrahive.llm import registry


def _entry(model_id: str, context_window: int) -> registry.ModelEntry:
    return registry.ModelEntry(
        id=model_id, provider="ollama", label=model_id,
        purposes=frozenset({"chat"}), context_window=context_window,
    )


def test_cached_context_window_reads_registry_cache(monkeypatch):
    monkeypatch.setattr(registry, "_cache", (0.0, [_entry("ollama/gemma4:latest", 131_072)]))
    assert registry.cached_context_window("ollama/gemma4:latest") == 131_072


def test_cached_context_window_none_when_cache_empty(monkeypatch):
    monkeypatch.setattr(registry, "_cache", None)
    assert registry.cached_context_window("ollama/gemma4:latest") is None


def test_cached_context_window_none_when_model_missing(monkeypatch):
    monkeypatch.setattr(registry, "_cache", (0.0, [_entry("ollama/qwen3:14b", 40_960)]))
    assert registry.cached_context_window("ollama/gemma4:latest") is None


def test_context_window_for_ollama_uses_registry_cache_not_default(monkeypatch):
    """Der eigentliche Bug: gemma4 bekam 8192 (Default) statt 131072."""
    monkeypatch.setattr(registry, "_cache", (0.0, [_entry("ollama/gemma4:latest", 131_072)]))
    # 131072 liegt über OLLAMA_NUM_CTX_CAP (32768) -> wird gedeckelt, aber
    # NICHT auf den 8192-Default zurückfallen.
    assert context_window_for("ollama/gemma4:latest") == 32_768


def test_context_window_for_ollama_within_cap_uses_exact_value(monkeypatch):
    monkeypatch.setattr(registry, "_cache", (0.0, [_entry("ollama/qwen3:14b", 40_960)]))
    assert context_window_for("ollama/qwen3:14b") == 32_768  # 40960 > cap -> gedeckelt


def test_context_window_for_ollama_falls_back_to_default_when_unknown(monkeypatch):
    monkeypatch.setattr(registry, "_cache", None)
    assert context_window_for("ollama/some-unknown-model:latest") == 8_192
