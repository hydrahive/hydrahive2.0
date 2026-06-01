"""Zentraler SSRF-Guard + butler http_post-Härtung (Issue #187)."""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.net.ssrf import validate_outbound_url


@pytest.mark.parametrize("url", [
    "https://8.8.8.8/path",          # öffentliche IP, kein DNS
    "http://93.184.216.34/",         # öffentliche IP
])
def test_validate_allows_public(url):
    assert validate_outbound_url(url) is None


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/x",            # loopback
    "http://localhost/x",            # denylist
    "http://10.0.0.5/x",             # RFC1918
    "http://192.168.1.1/x",
    "http://169.254.169.254/latest", # Cloud-Metadata
    "ftp://example.com/x",           # scheme
    "file:///etc/passwd",            # scheme
    "gopher://8.8.8.8/x",            # scheme
    "http:///nohost",                # kein Host
])
def test_validate_blocks(url):
    assert validate_outbound_url(url) is not None


def test_http_post_action_blocks_internal_target():
    from hydrahive.butler.models import TriggerEvent
    from hydrahive.butler.registry.actions import http_post

    event = TriggerEvent(event_type="webhook")
    res = asyncio.run(http_post._execute(
        {"url": "http://127.0.0.1:8765/internal", "body": ""}, event,
    ))
    assert res.ok is False
    assert "blocked" in res.detail.lower()


def test_fetch_url_is_blocked_still_importable():
    # Rückwärtskompatibel: _is_blocked bleibt über fetch_url erreichbar.
    from hydrahive.tools.fetch_url import _is_blocked
    assert _is_blocked("127.0.0.1") is True
    assert _is_blocked("8.8.8.8") is False
