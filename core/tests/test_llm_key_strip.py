"""LLM-Einstellungen: Leerzeichen/Zeilenumbrüche um einen eingefügten Key werden entfernt (Live-Fund 15.10.2026:
führendes Leerzeichen → httpx „Illegal header value“ → nur „Connection error.“ im Chat)."""
from __future__ import annotations

import pytest

from hydrahive.api.routes.llm import LlmProvider


@pytest.mark.parametrize("raw", [" sk-ant-oat01-abc", "sk-ant-oat01-abc\n", "\t sk-ant-oat01-abc \r\n"])
def test_key_wird_getrimmt(raw):
    p = LlmProvider(id="anthropic", name="Anthropic", api_key=raw, models=[])
    assert p.api_key == "sk-ant-oat01-abc"


def test_leerer_key_bleibt_leer():
    assert LlmProvider(id="x", name="X", api_key="   ", models=[]).api_key == ""


def test_client_trimmt_auch_alte_configs():
    from hydrahive.llm import _anthropic_calls as ac
    client, is_oauth = ac._client(" sk-ant-oat01-abc\n")
    assert is_oauth is True
    assert client.auth_token == "sk-ant-oat01-abc"
    client2, is_oauth2 = ac._client(" sk-ant-api03-xyz ")
    assert is_oauth2 is False and client2.api_key == "sk-ant-api03-xyz"
