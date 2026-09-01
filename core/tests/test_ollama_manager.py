from __future__ import annotations

import asyncio
import json

import pytest

from hydrahive.llm import ollama_fit, ollama_library, ollama_manager
from hydrahive.llm.ollama_client import parse_tags_response
from hydrahive.llm.ollama_common import normalize_model_name, validate_family_name


@pytest.fixture(autouse=True)
def _clear_fit_cache():
    ollama_fit._cache_clear()
    yield
    ollama_fit._cache_clear()


LIBRARY_HTML = """
<ul>
  <li class="flex border-b">
    <a href="/library/qwen3" class="group">
      <h2><span>qwen3</span></h2>
      <p class="max-w-lg text-md">A capable Qwen family.</p>
      <span class="bg-indigo-50">tools</span>
      <span class="bg-indigo-50">thinking</span>
      <span class="bg-[#ddf4ff]">8b</span>
      <span class="bg-[#ddf4ff]">14b</span>
    </a>
  </li>
  <li><a href="/library/nomic-embed-text"><h2><span>nomic-embed-text</span></h2>
    <p class="text-md">Embedding model.</p><span class="bg-indigo-50">embedding</span></a></li>
</ul>
"""

TAGS_HTML = """
<a href="/library/qwen3:8b" class="sm:hidden flex flex-col">
  <p>qwen3:8b</p><p class="flex text-neutral-500">5.2GB · 40K context window · Text · 1 year ago</p>
</a>
<a href="/library/qwen3:14b" class="sm:hidden flex flex-col">
  <p>qwen3:14b</p><p class="flex text-neutral-500">9.3GB · 40K context window · Text, Image · 1 year ago</p>
</a>
"""


def test_model_name_validation_rejects_urls_and_shell_syntax():
    assert normalize_model_name("ollama/qwen3:14b") == "qwen3:14b"
    for invalid in ("", "https://evil.test/x", "qwen3;rm", "../qwen3", "qwen3:tag space"):
        with pytest.raises(ValueError):
            normalize_model_name(invalid)


def test_family_validation_accepts_official_names_only():
    assert validate_family_name("qwen3.5") == "qwen3.5"
    with pytest.raises(ValueError):
        validate_family_name("vendor/model")


def test_parse_library_families_extracts_description_capabilities_and_sizes():
    rows = ollama_library.parse_library_families(LIBRARY_HTML)
    assert rows == [
        {
            "name": "qwen3",
            "description": "A capable Qwen family.",
            "capabilities": ["thinking", "tools"],
            "parameter_sizes": ["8b", "14b"],
        },
        {
            "name": "nomic-embed-text",
            "description": "Embedding model.",
            "capabilities": ["embedding"],
            "parameter_sizes": [],
        },
    ]


def test_parse_library_tags_extracts_size_context_and_modalities():
    rows = ollama_library.parse_library_tags("qwen3", TAGS_HTML)
    assert rows[0] == {
        "name": "qwen3:8b",
        "size": 5_200_000_000,
        "context_window": 40_000,
        "input_modalities": ["text"],
    }
    assert rows[1]["size"] == 9_300_000_000
    assert rows[1]["input_modalities"] == ["text", "image"]


def test_parse_tags_response_preserves_native_ollama_metadata():
    rows = parse_tags_response({"models": [{
        "name": "qwen3:14b", "size": 9_300_000_000, "digest": "abc",
        "modified_at": "2026-01-01T00:00:00Z",
        "details": {"family": "qwen3", "parameter_size": "14.8B", "quantization_level": "Q4_K_M"},
    }]})
    assert rows == [{
        "id": "ollama/qwen3:14b", "ollama_name": "qwen3:14b", "installed": True,
        "size": 9_300_000_000, "digest": "abc", "modified_at": "2026-01-01T00:00:00Z",
        "family": "qwen3", "parameter_size": "14.8B", "quantization": "Q4_K_M",
        "context_window": None, "capabilities": [], "input_modalities": [], "output_modalities": [],
    }]


def test_llmfit_rows_are_keyed_by_ollama_name(monkeypatch):
    async def fake_run(*args):
        if args[0] == "system":
            return {"total_ram_gb": 64, "gpu_name": "RTX", "gpu_vram_gb": 16}
        return {"models": [{
            "ollama_name": "qwen3:14b", "fit_level": "good", "score": 88.5,
            "memory_required_gb": 11.2, "memory_available_gb": 16,
            "estimated_tps": 24.5, "measured_tps": 26.1,
            "estimate_confidence": "measured_local", "run_mode": "gpu", "best_quant": "Q4_K_M",
        }]}

    monkeypatch.setattr(ollama_fit, "_run_json", fake_run)
    result = asyncio.run(ollama_fit.load_hardware_fit())
    assert result["available"] is True
    assert result["system"]["gpu_vram_gb"] == 16
    assert result["models"]["qwen3:14b"]["fit"] == "good"
    assert result["models"]["qwen3:14b"]["measured_tps"] == 26.1


def test_llmfit_missing_binary_degrades_without_catalog_failure(monkeypatch):
    async def missing(*args):
        raise FileNotFoundError

    monkeypatch.setattr(ollama_fit, "_run_json", missing)
    result = asyncio.run(ollama_fit.load_hardware_fit())
    assert result == {"available": False, "reason": "llmfit_not_installed", "system": None, "models": {}}


def test_own_lan_ip_receives_fit(monkeypatch):
    """Regression: Ollama unter der eigenen LAN-IP galt faelschlich als remote."""
    from hydrahive.llm import _local_host

    monkeypatch.setattr(_local_host, "_own_addresses", lambda: frozenset({"192.168.178.197"}))
    _local_host._cache_clear()

    async def fit():
        return {"available": True, "reason": None, "system": {"gpu_vram_gb": 16}, "models": {}}

    monkeypatch.setattr(ollama_manager.ollama_fit, "load_hardware_fit", fit)
    result = asyncio.run(ollama_manager._fit_for_provider({"api_base": "http://192.168.178.197:11434"}))
    assert result["available"] is True


def test_catalog_reports_effective_context_window(monkeypatch):
    """Der Katalog muss das genutzte Fenster nennen, nicht nur das theoretische."""
    row = {"id": "ollama/gemma4:latest", "ollama_name": "gemma4:latest",
           "installed": True, "context_window": 131_072}
    merged = ollama_manager._merge_fit(row, {}, free_vram=14.0)
    assert merged["context_window"] == 131_072
    assert merged["effective_context_window"] == 131_072

    tight = ollama_manager._merge_fit(row, {}, free_vram=4.0)
    assert tight["effective_context_window"] < 131_072


def test_remote_ollama_does_not_receive_fit_from_hydrahive_host(monkeypatch):
    called = False

    async def fit():
        nonlocal called
        called = True
        return {"available": True, "models": {}}

    monkeypatch.setattr(ollama_manager.ollama_fit, "load_hardware_fit", fit)
    result = asyncio.run(ollama_manager._fit_for_provider({"api_base": "http://192.0.2.10:11434"}))
    assert result["available"] is False
    assert result["reason"] == "llmfit_remote_ollama"
    assert called is False


def test_catalog_overview_keeps_local_models_when_library_is_offline(monkeypatch):
    async def local(_provider):
        return [{
            "id": "ollama/qwen3:14b", "ollama_name": "qwen3:14b", "installed": True,
            "family": "qwen3", "size": 9_300_000_000, "capabilities": ["completion", "tools"],
            "input_modalities": ["text"], "output_modalities": ["text"],
        }]

    async def library():
        raise RuntimeError("offline")

    async def fit():
        return {"available": True, "reason": None, "system": {"gpu_vram_gb": 16}, "models": {
            "qwen3:14b": {"fit": "good", "estimated_tps": 20.0},
        }}

    monkeypatch.setattr(ollama_manager.ollama_client, "list_installed", local)
    monkeypatch.setattr(ollama_manager.ollama_library, "list_families", library)
    monkeypatch.setattr(ollama_manager.ollama_fit, "load_hardware_fit", fit)
    result = asyncio.run(ollama_manager.catalog_overview({"id": "ollama", "api_base": "http://localhost:11434"}))
    assert result["connected"] is True
    assert result["library_error"] == "ollama_library_unavailable"
    assert result["installed_models"][0]["fit"] == "good"
    assert result["installed_models"][0]["estimated_tps"] == 20.0


def test_family_variants_merge_library_local_and_fit(monkeypatch):
    async def tags(_family):
        return [{"name": "qwen3:14b", "size": 9_300_000_000, "context_window": 40_000,
                 "input_modalities": ["text"]}]

    async def families():
        return [{"name": "qwen3", "description": "Qwen", "capabilities": ["tools", "thinking"],
                 "parameter_sizes": ["14b"]}]

    async def local(_provider):
        return [{"id": "ollama/qwen3:14b", "ollama_name": "qwen3:14b", "installed": True,
                 "family": "qwen3", "size": 9_200_000_000, "capabilities": ["completion", "tools"],
                 "input_modalities": ["text"], "output_modalities": ["text"], "quantization": "Q4_K_M"}]

    async def fit():
        return {"available": True, "reason": None, "system": None,
                "models": {"qwen3:14b": {"fit": "perfect", "score": 95}}}

    monkeypatch.setattr(ollama_manager.ollama_library, "list_tags", tags)
    monkeypatch.setattr(ollama_manager.ollama_library, "list_families", families)
    monkeypatch.setattr(ollama_manager.ollama_client, "list_installed", local)
    monkeypatch.setattr(ollama_manager.ollama_fit, "load_hardware_fit", fit)
    result = asyncio.run(ollama_manager.family_variants("qwen3", {"api_base": "http://localhost:11434"}))
    row = result["models"][0]
    assert row["installed"] is True
    assert row["quantization"] == "Q4_K_M"
    assert row["fit"] == "perfect"
    assert row["capabilities"] == ["completion", "thinking", "tools"]


def test_llmfit_rejects_oversized_or_invalid_json(monkeypatch):
    class Proc:
        returncode = 0

        async def communicate(self):
            return b"x" * (ollama_fit.MAX_OUTPUT_BYTES + 1), b""

    async def create(*args, **kwargs):
        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    with pytest.raises(ValueError, match="output_too_large"):
        asyncio.run(ollama_fit._run_json("fit", "--json"))

    async def invalid(*args):
        return json.loads("not json")

    # The adapter catches malformed command output at its system boundary.
    monkeypatch.setattr(ollama_fit, "_run_json", invalid)
    result = asyncio.run(ollama_fit.load_hardware_fit())
    assert result["available"] is False
    assert result["reason"] == "llmfit_failed"
