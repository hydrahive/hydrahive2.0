"""Tests für das query_health_data Agent-Tool (Contract: user_id-Weitergabe + Guards)."""
from __future__ import annotations

import asyncio
from pathlib import Path


def _run(coro):
    return asyncio.run(coro)


def _make_ctx(user_id: str):
    from hydrahive.tools.base import ToolContext
    return ToolContext(
        session_id="t",
        agent_id="",
        user_id=user_id,
        workspace=Path("/tmp"),
    )


def test_query_health_data_reicht_user_id_durch(monkeypatch):
    """Regression H1: Tool muss user_id aus dem Kontext an get_metrics_summary geben."""
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "testkey")

    captured: dict = {}

    def fake_summary(user_id, days=7, metric=None):
        captured["user_id"] = user_id
        captured["days"] = days
        captured["metric"] = metric
        return {"metrics": {"step_count": 5000}, "last_ingest": "2026-05-28"}

    import hydrahive.tools.health_data as mod
    monkeypatch.setattr(mod.health_db, "get_metrics_summary", fake_summary)

    from hydrahive.tools.health_data import TOOL
    result = _run(TOOL.execute({"days": 30, "metric": "step_count"}, _make_ctx("testuser")))

    assert result.success
    assert captured["user_id"] == "testuser"
    assert captured["days"] == 30
    assert captured["metric"] == "step_count"


def test_query_health_data_ohne_user_kontext_faellt_ab(monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "testkey")

    from hydrahive.tools.health_data import TOOL
    result = _run(TOOL.execute({}, _make_ctx("")))

    assert not result.success
    assert "User-Kontext" in (result.error or "")


def test_query_health_data_ohne_api_key_faellt_ab(monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "")

    from hydrahive.tools.health_data import TOOL
    result = _run(TOOL.execute({}, _make_ctx("testuser")))

    assert not result.success
    assert "HH_HEALTH_API_KEY" in (result.error or "")
