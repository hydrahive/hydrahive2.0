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
async def test_create_scan_requires_session_id():
    with patch.object(AigClient, "_request", new=AsyncMock(return_value={})):
        with pytest.raises(AigError, match="aig_missing_session_id"):
            await AigClient().create_infra_scan("http://127.0.0.1:11434")


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
