"""Regressionstests für ehrliche Butler-Platzhalter-Aktionen."""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.butler.executor import dispatch
from hydrahive.butler.models import Edge, Flow, Node, NodePosition, TriggerEvent
from hydrahive.butler.registry import ACTIONS, all_specs, load_builtins

NOT_IMPLEMENTED = "not_implemented: Diese Aktion ist noch nicht verfügbar"
STUB_ACTIONS = (
    "send_email",
    "git_create_issue",
    "git_add_comment",
    "discord_post",
)


@pytest.fixture(autouse=True)
def _registry() -> None:
    load_builtins()


def _flow(action_subtype: str) -> Flow:
    position = NodePosition(x=0, y=0)
    return Flow(
        flow_id="stub-flow",
        name="Stub flow",
        owner="testuser",
        nodes=[
            Node(
                id="trigger",
                type="trigger",
                subtype="message_received",
                position=position,
                params={"channel": "all"},
            ),
            Node(
                id="action",
                type="action",
                subtype=action_subtype,
                position=position,
            ),
        ],
        edges=[Edge(id="edge", source="trigger", target="action")],
    )


@pytest.mark.parametrize("subtype", STUB_ACTIONS)
def test_stub_action_reports_not_implemented(subtype: str) -> None:
    spec = ACTIONS[subtype]

    result = asyncio.run(spec.execute({}, TriggerEvent(event_type="message")))

    assert getattr(spec, "implemented", True) is False
    assert result.ok is False
    assert result.detail == NOT_IMPLEMENTED


def test_registry_metadata_marks_stub_actions_not_implemented() -> None:
    actions = {item["subtype"]: item for item in all_specs()["actions"]}

    assert {subtype for subtype in STUB_ACTIONS if actions[subtype]["implemented"] is False} == set(
        STUB_ACTIONS
    )


def test_dry_run_calls_out_not_implemented_action() -> None:
    result = asyncio.run(
        dispatch(
            _flow("send_email"),
            TriggerEvent(event_type="message", channel="all"),
            dry_run=True,
        )
    )

    action_trace = next(item for item in result["trace"] if item["node_id"] == "action")
    assert action_trace == {
        "node_id": "action",
        "type": "action",
        "subtype": "send_email",
        "label": None,
        "decision": "not_implemented",
        "ok": False,
        "detail": NOT_IMPLEMENTED,
    }
    assert result["actions_executed"] == []


def test_flow_reports_stub_action_as_failed() -> None:
    result = asyncio.run(
        dispatch(
            _flow("git_add_comment"),
            TriggerEvent(event_type="message", channel="all"),
        )
    )

    assert result["actions_executed"][0]["ok"] is False
    assert result["actions_executed"][0]["detail"] == NOT_IMPLEMENTED
    action_trace = next(item for item in result["trace"] if item["node_id"] == "action")
    assert action_trace["decision"] == "executed"
    assert action_trace["ok"] is False


def test_stub_action_flow_can_be_created_loaded_and_saved(client, auth_headers) -> None:
    flow = _flow("discord_post")
    payload = flow.model_dump(exclude={"owner", "created_at", "updated_at"}, mode="json")

    created = client.post("/api/butler/flows", headers=auth_headers, json=payload)
    assert created.status_code == 201, created.text

    loaded = client.get("/api/butler/flows/stub-flow", headers=auth_headers)
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["nodes"][1]["subtype"] == "discord_post"

    payload["name"] = "Saved stub flow"
    saved = client.put("/api/butler/flows/stub-flow", headers=auth_headers, json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["name"] == "Saved stub flow"
