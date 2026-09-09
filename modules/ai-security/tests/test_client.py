"""AIG-Client-Fehlergrenzen und Report-Redaction."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.aig_client import AigClient, AigError
from backend.service import encode_result


def test_result_redacts_nested_secrets():
    encoded = encode_result(
        {"model": {"api_key": "secret", "name": "local"}, "items": [{"token": "x"}]},
        10000,
    )
    assert "secret" not in encoded
    assert "[REDACTED]" in encoded


def test_result_is_bounded():
    encoded = encode_result({"text": "x" * 10000}, 100)
    assert encoded == '{"truncated":true,"reason":"result_too_large"}'


@pytest.mark.asyncio
async def test_create_scan_includes_configured_model(monkeypatch):
    monkeypatch.setenv("HH_AI_SECURITY_MODEL", "gemma4:latest")
    monkeypatch.setenv("HH_AI_SECURITY_MODEL_TOKEN", "ollama")
    monkeypatch.setenv("HH_AI_SECURITY_MODEL_BASE_URL", "http://ollama:11434/v1")
    request = AsyncMock(return_value={"session_id": "scan-1"})
    with patch.object(AigClient, "_request", new=request):
        assert await AigClient().create_infra_scan("http://127.0.0.1:11434") == "scan-1"
    payload = request.call_args.kwargs["json"]["content"]
    assert payload["model"] == {
        "model": "gemma4:latest",
        "token": "ollama",
        "base_url": "http://ollama:11434/v1",
    }


@pytest.mark.asyncio
async def test_create_scan_requires_session_id():
    with patch.object(AigClient, "_request", new=AsyncMock(return_value={})):
        with pytest.raises(AigError, match="aig_missing_session_id"):
            await AigClient().create_infra_scan("http://127.0.0.1:11434")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("upstream_status", "expected_status"),
    [("done", "completed"), ("error", "failed")],
)
async def test_status_maps_aig_terminal_states(upstream_status, expected_status):
    request = AsyncMock(return_value={"status": upstream_status})
    with patch.object(AigClient, "_request", new=request):
        assert await AigClient().status("scan-1") == expected_status


@pytest.mark.asyncio
async def test_health_accepts_a_successful_runtime_response():
    class Stream:
        async def __aenter__(self):
            return httpx.Response(
                200,
                text="ok",
                request=httpx.Request("GET", "http://127.0.0.1:8088/"),
            )

        async def __aexit__(self, *_args):
            return None

    with patch("httpx.AsyncClient.stream", return_value=Stream()):
        await AigClient().health()


@pytest.mark.asyncio
async def test_client_rejects_non_json_upstream():
    class Stream:
        def __init__(self, response):
            self.response = response

        async def __aenter__(self):
            return self.response

        async def __aexit__(self, *_args):
            return None

    response = httpx.Response(
        200,
        text="not-json",
        request=httpx.Request("POST", "http://127.0.0.1:8088/api/v1/app/taskapi/tasks"),
    )
    with patch("httpx.AsyncClient.stream", return_value=Stream(response)):
        with pytest.raises(AigError, match="aig_invalid_json"):
            await AigClient().create_infra_scan("http://127.0.0.1:11434")
