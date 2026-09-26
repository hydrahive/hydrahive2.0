"""Polling-Statusübergänge und Fehlerisolation."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend import jobs, service


@pytest.mark.asyncio
async def test_completed_scan_downloads_and_redacts_result(client, alice, monkeypatch):
    from backend import routes

    class FakeClient:
        create_infra_scan = AsyncMock(return_value="job-1")
        status = AsyncMock(return_value="completed")
        result = AsyncMock(return_value={"finding": {"api_key": "secret"}})

    monkeypatch.setattr(routes, "AigClient", FakeClient)
    monkeypatch.setattr(jobs, "AigClient", FakeClient)
    response = client.post(
        "/api/modules/ai-security/scans",
        json={"target_url": "http://127.0.0.1:11434"},
        headers=alice,
    )
    assert response.status_code == 202
    await jobs.poll_scans()
    scan = client.get(
        f"/api/modules/ai-security/scans/{response.json()['id']}", headers=alice
    ).json()
    assert scan["status"] == "completed"
    assert scan["result"]["finding"]["api_key"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_failed_upstream_scan_is_recorded(client, alice, monkeypatch):
    from backend import routes

    class FakeClient:
        create_infra_scan = AsyncMock(return_value="job-2")
        status = AsyncMock(return_value="failed")

    monkeypatch.setattr(routes, "AigClient", FakeClient)
    monkeypatch.setattr(jobs, "AigClient", FakeClient)
    response = client.post(
        "/api/modules/ai-security/scans",
        json={"target_url": "http://127.0.0.1:11434"},
        headers=alice,
    )
    await jobs.poll_scans()
    scan = client.get(
        f"/api/modules/ai-security/scans/{response.json()['id']}", headers=alice
    ).json()
    assert scan["status"] == "failed"
    assert scan["error_code"] == "upstream_scan_failed"
