"""Butler-Editor zeigt Bausteine aus Modulen (docs/specs/butler-module-nodes.md §3, §5).

Die Brücke merkt sich, welcher Baustein von welchem Modul kam; ``GET /api/butler/registry`` liefert nur diese – mit
Beschreibung und vollem ParamSchema, damit die Oberfläche das Formular bauen kann.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import hydrahive.butler.registry as reg
from hydrahive.butler.registry import ActionResult, ActionSpec, ConditionSpec, ParamSchema, TriggerSpec
from hydrahive.modules import butler_bridge
from hydrahive.modules.context import ModuleContext
from hydrahive.modules.manifest import ModuleManifest
from hydrahive.modules.registry import LoadedModule


def _loaded(mid: str, ctx: ModuleContext) -> LoadedModule:
    return LoadedModule(name=mid, manifest=ModuleManifest(id=mid, name=mid, version="1.0.0"), path=Path("."), ctx=ctx,
                        loaded=True)


@pytest.fixture
def demo_module(monkeypatch):
    reg.load_builtins()                     # zuerst: registriert nur beim ersten Import – Schnappschuss danach
    snap = (dict(reg.TRIGGERS), dict(reg.CONDITIONS), dict(reg.ACTIONS), dict(butler_bridge.MODULE_SUBTYPES))
    ctx = ModuleContext("demo")
    ctx.register_butler_trigger(TriggerSpec(
        subtype="demo_call_incoming", label="Anruf kommt rein", description="Feuert beim Klingeln.",
        params=[ParamSchema(key="numbers", label="Nur diese Nummern", kind="list_text", placeholder="030 1234567")],
        matches=lambda p, e: True))
    ctx.register_butler_condition(ConditionSpec(
        subtype="demo_caller", label="Anrufer-Nummer", description="Prüft die Nummer.",
        params=[ParamSchema(key="mode", label="Art", kind="select", required=True, options=["starts", "anonymous"],
                            default="starts")],
        evaluate=lambda p, e: True))
    ctx.register_butler_action(ActionSpec(
        subtype="demo_answer", label="Annehmen", description="Nimmt an.", params=[], implemented=False,
        execute=lambda p, e: ActionResult(ok=True)))
    ctx.register_butler_action(ActionSpec(                       # kollidiert mit eingebautem Baustein
        subtype="reply_fixed", label="Kaputt", description="x", params=[], execute=lambda p, e: ActionResult(ok=True)))
    monkeypatch.setattr(butler_bridge, "REGISTRY", {"demo": _loaded("demo", ctx)})
    butler_bridge.register_module_butler_subtypes()
    yield
    reg.TRIGGERS.clear(); reg.TRIGGERS.update(snap[0])
    reg.CONDITIONS.clear(); reg.CONDITIONS.update(snap[1])
    reg.ACTIONS.clear(); reg.ACTIONS.update(snap[2])
    butler_bridge.MODULE_SUBTYPES.clear(); butler_bridge.MODULE_SUBTYPES.update(snap[3])


def test_bruecke_merkt_sich_das_modul(demo_module) -> None:
    assert butler_bridge.MODULE_SUBTYPES[("trigger", "demo_call_incoming")] == "demo"
    assert butler_bridge.MODULE_SUBTYPES[("condition", "demo_caller")] == "demo"
    assert ("action", "reply_fixed") not in butler_bridge.MODULE_SUBTYPES, "übersprungene Kollision zählt nicht"
    assert reg.ACTIONS["reply_fixed"].label != "Kaputt", "eingebauter Baustein bleibt"


def test_route_liefert_nur_modul_bausteine_mit_schema(client, auth_headers, demo_module) -> None:
    r = client.get("/api/butler/registry", headers=auth_headers)
    assert r.status_code == 200
    items = {i["subtype"]: i for i in r.json()["nodes"]}
    assert set(items) == {"demo_call_incoming", "demo_caller", "demo_answer"}, "keine eingebauten, keine Kollision"
    t = items["demo_call_incoming"]
    assert t["type"] == "trigger" and t["module"] == "demo" and t["label"] == "Anruf kommt rein"
    assert t["description"] == "Feuert beim Klingeln." and t["implemented"] is True
    assert t["params"] == [{"key": "numbers", "label": "Nur diese Nummern", "kind": "list_text", "required": False,
                            "options": [], "placeholder": "030 1234567", "default": None}]
    c = items["demo_caller"]
    assert c["type"] == "condition" and c["params"][0]["options"] == ["starts", "anonymous"]
    assert c["params"][0]["default"] == "starts" and c["params"][0]["required"] is True
    assert items["demo_answer"]["type"] == "action" and items["demo_answer"]["implemented"] is False


def test_route_ohne_module_leer(client, auth_headers, monkeypatch) -> None:
    monkeypatch.setattr(butler_bridge, "MODULE_SUBTYPES", {})
    assert client.get("/api/butler/registry", headers=auth_headers).json() == {"nodes": []}


def test_route_braucht_anmeldung(client) -> None:
    assert client.get("/api/butler/registry").status_code == 401


def test_flow_mit_modul_baustein_speicherbar(client, auth_headers, demo_module) -> None:
    body = {"flow_id": "anruf-test", "name": "Anruf Test", "enabled": False, "nodes": [
        {"id": "t1", "type": "trigger", "subtype": "demo_call_incoming", "position": {"x": 0, "y": 0},
         "params": {"numbers": ["030 1234567"]}},
        {"id": "a1", "type": "action", "subtype": "demo_answer", "position": {"x": 200, "y": 0}, "params": {}}],
        "edges": [{"id": "e1", "source": "t1", "target": "a1", "source_handle": "output"}]}
    r = client.post("/api/butler/flows", json=body, headers=auth_headers)
    assert r.status_code == 201, r.text
