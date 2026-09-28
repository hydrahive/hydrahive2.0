"""Butler: Speichern prüft Bausteine gegen die Registry.

Vorher konnte die UI Bedingungen anbieten, die der Server nicht kennt
(z. B. ``contact_known``). Der Flow ließ sich speichern und aktivieren, endete
beim Ausführen aber still. Jetzt lehnt der Server unbekannte Subtypes mit 400 ab
und nennt sie im Fehler. Bereits gespeicherte Flows laden weiter.
"""
from __future__ import annotations

import asyncio
import logging

import pytest

from hydrahive.butler.models import Edge, Flow, Node, NodePosition, TriggerEvent
from hydrahive.butler.registry import (
    CONDITIONS, ConditionSpec, load_builtins, register_condition,
)
from hydrahive.butler.registry._validation import unknown_subtypes


@pytest.fixture(autouse=True)
def _registry():
    load_builtins()


def _pos() -> NodePosition:
    return NodePosition(x=0, y=0)


def _flow(condition_subtype: str, action_subtype: str = "ignore",
          flow_id: str = "f1") -> Flow:
    return Flow(
        flow_id=flow_id, name="Test", owner="testuser",
        nodes=[
            Node(id="t", type="trigger", subtype="message_received", position=_pos()),
            Node(id="c", type="condition", subtype=condition_subtype, position=_pos(),
                 params={"keyword": "x"}),
            Node(id="a", type="action", subtype=action_subtype, position=_pos()),
        ],
        edges=[
            Edge(id="e1", source="t", target="c"),
            Edge(id="e2", source="c", target="a", source_handle="true"),
        ],
    )


def _payload(condition_subtype: str, action_subtype: str = "ignore",
             flow_id: str = "f1") -> dict:
    flow = _flow(condition_subtype, action_subtype, flow_id)
    return {
        "flow_id": flow.flow_id, "name": flow.name, "enabled": True,
        "nodes": [n.model_dump() for n in flow.nodes],
        "edges": [e.model_dump() for e in flow.edges],
    }


def test_unknown_subtypes_nennt_jeden_fremden_baustein():
    flow = _flow("contact_known", "send_fax")
    assert unknown_subtypes(flow) == ["contact_known", "send_fax"]


def test_unknown_subtypes_leer_bei_bekannten_bausteinen():
    assert unknown_subtypes(_flow("message_contains")) == []


def test_speichern_mit_unbekannter_bedingung_liefert_400(client, auth_headers):
    r = client.post("/api/butler/flows", headers=auth_headers,
                    json=_payload("contact_known"))
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["code"] == "butler_subtype_unknown"
    assert "contact_known" in detail["params"]["subtypes"]


def test_speichern_mit_bekannten_bausteinen_liefert_201(client, auth_headers):
    r = client.post("/api/butler/flows", headers=auth_headers,
                    json=_payload("message_contains", flow_id="f-bekannt"))
    assert r.status_code == 201, r.text


def test_modul_subtype_in_registry_wird_akzeptiert(client, auth_headers):
    register_condition(ConditionSpec(
        subtype="modul_test_cond", label="Modul", description="",
        params=[], evaluate=lambda p, e: True,
    ))
    try:
        r = client.post("/api/butler/flows", headers=auth_headers,
                        json=_payload("modul_test_cond", flow_id="f-modul"))
        assert r.status_code == 201, r.text
    finally:
        CONDITIONS.pop("modul_test_cond", None)


def test_aktualisieren_mit_unbekannter_bedingung_liefert_400(client, auth_headers):
    r = client.post("/api/butler/flows", headers=auth_headers,
                    json=_payload("message_contains", flow_id="f-update"))
    assert r.status_code == 201, r.text
    r = client.put("/api/butler/flows/f-update", headers=auth_headers,
                   json=_payload("git_branch_is", flow_id="f-update"))
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "butler_subtype_unknown"


def test_executor_warnt_bei_unbekannter_bedingung(caplog):
    from hydrahive.butler import executor

    flow = _flow("contact_known")
    event = TriggerEvent(event_type="message", channel="whatsapp", message_text="x")
    with caplog.at_level(logging.WARNING, logger="hydrahive.butler.executor"):
        result = asyncio.run(executor.dispatch(flow, event))
    assert result["matched"] is True
    assert any(t.get("decision") == "unknown_condition" for t in result["trace"])
    assert any("contact_known" in rec.getMessage() for rec in caplog.records)
