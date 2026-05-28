"""Smoke-Tests für query_fhir_data Agent-Tool."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


def _run(coro):
    return asyncio.run(coro)


def _make_ctx():
    from hydrahive.tools.base import ToolContext
    return ToolContext(
        session_id="smoke",
        agent_id="",
        user_id="testuser",
        workspace=Path("/tmp"),
    )


def _insert_test_data(client, auth_headers):
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": {
                "resourceType": "Condition", "id": "c1",
                "code": {"coding": [{"code": "I10", "display": "Hypertonie"}]},
                "clinicalStatus": {"coding": [{"code": "active"}]},
            }},
            {"resource": {
                "resourceType": "Observation", "id": "o1",
                "code": {"text": "HbA1c"},
                "valueQuantity": {"value": 6.2, "unit": "%"},
                "effectiveDateTime": "2024-03-01",
            }},
        ],
    }
    client.post("/api/fhir/import", json=bundle, headers=auth_headers)


def test_query_all_types(client, auth_headers):
    _insert_test_data(client, auth_headers)
    from hydrahive.tools.fhir_data import TOOL
    ctx = _make_ctx()
    result = _run(TOOL.execute({}, ctx))
    assert result.success
    assert result.output["count"] >= 2


def test_query_by_type(client, auth_headers):
    _insert_test_data(client, auth_headers)
    from hydrahive.tools.fhir_data import TOOL
    ctx = _make_ctx()
    result = _run(TOOL.execute({"resource_types": ["Condition"]}, ctx))
    assert result.success
    assert "Hypertonie" in result.output["data"]


def test_query_fulltext(client, auth_headers):
    _insert_test_data(client, auth_headers)
    from hydrahive.tools.fhir_data import TOOL
    ctx = _make_ctx()
    result = _run(TOOL.execute({"search_text": "HbA1c"}, ctx))
    assert result.success
    assert result.output["count"] >= 1


def test_query_empty_returns_message(client, auth_headers):
    from hydrahive.tools.fhir_data import TOOL
    ctx = _make_ctx()
    result = _run(TOOL.execute({"search_text": "xyznotexistent123"}, ctx))
    assert result.success
    assert "Keine" in result.output["message"]
