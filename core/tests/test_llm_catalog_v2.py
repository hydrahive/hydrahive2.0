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


async def test_tool_probe_marks_only_a_real_native_tool_call_verified(monkeypatch):
    from hydrahive.llm import capability_probe

    async def fake_call(model, **kwargs):
        assert kwargs["tools"][0]["name"] == capability_probe.PROBE_TOOL_NAME
        return ([{
            "type": "tool_use",
            "id": "probe-call-1",
            "name": capability_probe.PROBE_TOOL_NAME,
            "input": {"value": "ok"},
        }], "tool_use", {})

    monkeypatch.setattr(capability_probe, "_call_probe_model", fake_call)
    monkeypatch.setattr(capability_probe, "_declared", lambda model: True)
    result = await capability_probe.probe_tools("ollama/gemma4:latest", node_id="wks-01")

    assert result["status"] == "verified"
    assert result["declared"] is True
    assert result["details"] == "native_tool_call_and_safe_dispatch"


async def test_tool_probe_rejects_text_imitation(monkeypatch):
    from hydrahive.llm import capability_probe

    async def fake_call(model, **kwargs):
        return ([{"type": "text", "text": '{"tool_calls": [{"name": "catalog_probe_echo"}]}'}], "end_turn", {})

    monkeypatch.setattr(capability_probe, "_call_probe_model", fake_call)
    result = await capability_probe.probe_tools("ollama/gemma4:latest", node_id="wks-01")

    assert result["status"] == "failed"
    assert result["details"] == "no_native_tool_call"


def test_capability_probe_endpoint_is_admin_only(client, auth_headers):
    response = client.post(
        "/api/llm/catalog/probes",
        headers=auth_headers,
        json={"model": "ollama/gemma4:latest"},
    )
    assert response.status_code == 403


def test_admin_can_start_capability_probe(client, admin_headers, monkeypatch):
    from hydrahive.api.routes import llm_catalog

    monkeypatch.setattr(
        llm_catalog.ollama_manager,
        "configured_provider",
        lambda: {"id": "ollama", "name": "Remote Ollama"},
    )

    async def start(model, *, node_id):
        assert model == "ollama/gemma4:latest"
        assert node_id == "provider:ollama"
        return {"id": "probe-1", "model": model, "node_id": node_id, "status": "queued"}

    monkeypatch.setattr(llm_catalog.capability_probe, "start_probe", start)
    response = client.post(
        "/api/llm/catalog/probes",
        headers=admin_headers,
        json={"model": "ollama/gemma4:latest"},
    )
    assert response.status_code == 202
    assert response.json()["id"] == "probe-1"


async def test_benchmark_reports_prompt_and_completion_rates(monkeypatch):
    from hydrahive.llm import benchmark

    async def fake_call(model, **kwargs):
        return {"input_tokens": 100, "output_tokens": 50}

    ticks = iter([10.0, 12.5])
    monkeypatch.setattr(benchmark, "_call_benchmark_model", fake_call)
    monkeypatch.setattr(benchmark.time, "perf_counter", lambda: next(ticks))
    result = await benchmark.run_benchmark("ollama/gemma4:latest", node_id="wks-01")

    assert result["status"] == "completed"
    assert result["prompt_tokens"] == 100
    assert result["completion_tokens"] == 50
    assert result["prompt_tps"] == 40.0
    assert result["completion_tps"] == 20.0


def test_benchmark_endpoint_is_admin_only(client, auth_headers):
    response = client.post(
        "/api/llm/catalog/benchmarks",
        headers=auth_headers,
        json={"model": "ollama/gemma4:latest"},
    )
    assert response.status_code == 403
