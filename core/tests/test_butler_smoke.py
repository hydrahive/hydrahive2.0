"""Smoke-Tests für den Butler — Flow-Validierung und Executor-Dispatch."""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.butler.models import Edge, Flow, Node, NodePosition, TriggerEvent
from hydrahive.butler.registry import load_builtins

load_builtins()


def _run(coro):
    return asyncio.run(coro)


def _pos() -> NodePosition:
    return NodePosition(x=0, y=0)


def _minimal_flow(**overrides) -> dict:
    base = {
        "flow_id": "smoke-flow",
        "name": "Smoke Flow",
        "owner": "testuser",
        "enabled": True,
        "nodes": [
            {"id": "t1", "type": "trigger", "subtype": "message_received",
             "position": {"x": 0, "y": 0}, "params": {"channel": "all"}},
            {"id": "a1", "type": "action", "subtype": "reply_fixed",
             "position": {"x": 200, "y": 0}, "params": {"text": "Bin weg."}},
        ],
        "edges": [
            {"id": "e1", "source": "t1", "target": "a1", "source_handle": "output"},
        ],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Flow-Validierung
# ---------------------------------------------------------------------------

def test_flow_valid_graph():
    flow = Flow(**_minimal_flow())
    assert flow.flow_id == "smoke-flow"
    assert len(flow.nodes) == 2


def test_flow_rejects_multiple_triggers():
    data = _minimal_flow()
    data["nodes"].append(
        {"id": "t2", "type": "trigger", "subtype": "cron_fired",
         "position": {"x": 0, "y": 100}, "params": {}}
    )
    with pytest.raises(Exception, match="multiple_triggers"):
        Flow(**data)


def test_flow_rejects_cycle():
    data = _minimal_flow()
    data["edges"].append(
        {"id": "e_back", "source": "a1", "target": "t1", "source_handle": "output"}
    )
    with pytest.raises(Exception, match="cycle_detected"):
        Flow(**data)


def test_flow_rejects_orphan_action():
    data = _minimal_flow()
    data["nodes"].append(
        {"id": "a_orphan", "type": "action", "subtype": "ignore",
         "position": {"x": 400, "y": 0}, "params": {}}
    )
    with pytest.raises(Exception, match="orphan_action"):
        Flow(**data)


# ---------------------------------------------------------------------------
# Executor — dispatch (sync-Wrapper via asyncio.run, Projekt-Muster)
# ---------------------------------------------------------------------------

def test_dispatch_dry_run_matches():
    from hydrahive.butler.executor import dispatch

    flow = Flow(**_minimal_flow())
    event = TriggerEvent(
        event_type="message", channel="whatsapp",
        message_text="hallo", owner="testuser",
    )
    result = _run(dispatch(flow, event, dry_run=True))
    assert result["matched"] is True
    nodes_visited = [t["node_id"] for t in result["trace"]]
    assert "t1" in nodes_visited
    assert "a1" in nodes_visited


def test_dispatch_no_match_wrong_event_type():
    from hydrahive.butler.executor import dispatch

    flow = Flow(**_minimal_flow())
    event = TriggerEvent(event_type="cron", owner="testuser")
    result = _run(dispatch(flow, event, dry_run=True))
    assert result["matched"] is False


def test_dispatch_executes_action():
    from hydrahive.butler.executor import dispatch

    flow = Flow(**_minimal_flow())
    event = TriggerEvent(
        event_type="message", channel="telegram",
        message_text="ping", owner="testuser",
    )
    result = _run(dispatch(flow, event, dry_run=False))
    assert result["matched"] is True
    replies = [a for a in result["actions_executed"] if a.get("reply_text")]
    assert replies, "reply_fixed action should set reply_text"
    assert replies[0]["reply_text"] == "Bin weg."
    assert replies[0]["stop_default"] is True
