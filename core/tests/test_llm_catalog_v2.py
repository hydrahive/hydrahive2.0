from __future__ import annotations

from hydrahive.llm import node_context


def test_provider_without_explicit_node_gets_stable_legacy_node_identity(monkeypatch):
    monkeypatch.setattr(node_context.node_db, "get_node", lambda node_id: None)

    result = node_context.for_provider({"id": "ollama", "name": "Ollama"})

    assert result == {
        "node_id": "provider:ollama",
        "node_name": "Ollama",
        "node_kind": "provider",
        "node_status": "configured",
        "hardware_source": "unknown",
    }


def test_explicit_compute_node_is_public_without_endpoint_or_secrets(monkeypatch):
    class _Node:
        node_id = "wks-01"
        name = "GPU Workstation"
        kind = "agent"
        status = "online"
        capabilities = {"llm": ["ollama"]}
        resources = {"gpu_name": "RTX", "gpu_vram_gb": 16}

    monkeypatch.setattr(node_context.node_db, "get_node", lambda node_id: _Node())

    result = node_context.for_provider({
        "id": "ollama",
        "name": "Remote Ollama",
        "node_id": "wks-01",
        "api_base": "http://10.0.0.20:11434",
        "api_key": "secret-never-returned",
    })

    assert result == {
        "node_id": "wks-01",
        "node_name": "GPU Workstation",
        "node_kind": "agent",
        "node_status": "online",
        "hardware_source": "compute_node",
    }
    assert "api_base" not in result
    assert "api_key" not in result


def test_unknown_explicit_node_does_not_fall_back_to_core_hardware(monkeypatch):
    monkeypatch.setattr(node_context.node_db, "get_node", lambda node_id: None)

    result = node_context.for_provider({
        "id": "ollama",
        "name": "Remote Ollama",
        "node_id": "missing-node",
    })

    assert result["node_id"] == "missing-node"
    assert result["node_status"] == "unknown"
    assert result["hardware_source"] == "unknown"
