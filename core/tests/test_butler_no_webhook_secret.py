"""Totes Pro-Flow webhook_secret entfernt (Issue #188).

Das Feld wurde nie verifiziert, aber in GET /api/butler/flows an alle Lese-User
geleakt. Entfernt → kein Pseudo-Secret mehr im Response. Gespeicherte Alt-Flows
mit dem Feld müssen weiter laden (Pydantic ignoriert Extra-Keys).
"""
from __future__ import annotations


def _minimal_flow_dict(**overrides) -> dict:
    base = {
        "flow_id": "f1", "name": "F", "owner": "u", "enabled": True,
        "nodes": [
            {"id": "t1", "type": "trigger", "subtype": "webhook_received",
             "position": {"x": 0, "y": 0}, "params": {}},
            {"id": "a1", "type": "action", "subtype": "ignore",
             "position": {"x": 200, "y": 0}, "params": {}},
        ],
        "edges": [{"id": "e1", "source": "t1", "target": "a1", "source_handle": "output"}],
    }
    base.update(overrides)
    return base


def test_flow_has_no_webhook_secret_field():
    from hydrahive.butler.models import Flow
    flow = Flow(**_minimal_flow_dict())
    assert "webhook_secret" not in flow.model_dump(), "darf nicht mehr exponiert werden"
    assert not hasattr(flow, "webhook_secret")


def test_legacy_flow_with_webhook_secret_still_loads():
    import json
    from hydrahive.butler.models import Flow
    legacy = _minimal_flow_dict(webhook_secret="old-leaked-secret")
    flow = Flow.model_validate_json(json.dumps(legacy))
    assert flow.flow_id == "f1"
    assert "webhook_secret" not in flow.model_dump()
