"""Butler-Executor — DFS-Traversal mit Trace-Sammlung.

`dispatch(flow, event, dry_run=False)` läuft einen Flow gegen ein Event
und liefert eine Trace-Liste der durchlaufenen Nodes inkl. Decisions
und Action-Resultate. Im Dry-Run werden Actions NICHT ausgeführt,
sondern nur als `would_execute` markiert.

`dispatch_event(event, owner)` iteriert alle Flows des Owners und
ruft dispatch pro matching-Flow.
"""
from __future__ import annotations

import logging
from typing import Any

from hydrahive.butler import persistence as bp
from hydrahive.butler.models import Flow, TriggerEvent
from hydrahive.butler.registry import ACTIONS, CONDITIONS, TRIGGERS

logger = logging.getLogger(__name__)
_MAX_DEPTH = 30


def _trace_node(node, **extra) -> dict[str, Any]:
    return {"node_id": node.id, "type": node.type, "subtype": node.subtype,
            "label": node.label, **extra}


async def dispatch(flow: Flow, event: TriggerEvent, *, dry_run: bool = False) -> dict:
    """Liefert {matched, trace, actions_executed}."""
    trace: list[dict] = []
    actions_executed: list[dict] = []

    triggers = [n for n in flow.nodes if n.type == "trigger"]
    if not triggers:
        return {"matched": False, "trace": trace, "actions_executed": actions_executed}
    tnode = triggers[0]
    tspec = TRIGGERS.get(tnode.subtype)
    if not tspec:
        trace.append(_trace_node(tnode, decision="unknown_trigger"))
        return {"matched": False, "trace": trace, "actions_executed": actions_executed}

    matched = tspec.matches(tnode.params, event)
    trace.append(_trace_node(tnode, decision="match" if matched else "no_match"))
    if not matched:
        return {"matched": False, "trace": trace, "actions_executed": actions_executed}

    await _traverse(flow, tnode.id, "output", event, trace,
                    actions_executed, dry_run, depth=0)
    return {"matched": True, "trace": trace, "actions_executed": actions_executed}


async def _traverse(flow, node_id, handle, event, trace, actions_executed,
                    dry_run, depth):
    if depth > _MAX_DEPTH:
        trace.append({"node_id": node_id, "decision": "max_depth_reached"})
        return
    for edge in flow.edges:
        if edge.source != node_id or edge.source_handle != handle:
            continue
        target = next((n for n in flow.nodes if n.id == edge.target), None)
        if not target:
            continue
        if target.type == "condition":
            await _run_condition(flow, target, event, trace, actions_executed,
                                 dry_run, depth)
        elif target.type == "action":
            await _run_action(flow, target, event, trace, actions_executed,
                              dry_run, depth)


async def _run_condition(flow, node, event, trace, actions_executed, dry_run, depth):
    spec = CONDITIONS.get(node.subtype)
    if not spec:
        trace.append(_trace_node(node, decision="unknown_condition"))
        return
    try:
        ok = spec.evaluate(node.params, event)
    except Exception as e:
        logger.warning("Condition %s crashed: %s", node.subtype, e)
        trace.append(_trace_node(node, decision="error", detail=str(e)))
        return
    trace.append(_trace_node(node, decision="true" if ok else "false"))
    next_handle = "true" if ok else "false"
    await _traverse(flow, node.id, next_handle, event, trace,
                    actions_executed, dry_run, depth + 1)


async def _run_action(flow, node, event, trace, actions_executed, dry_run, depth):
    spec = ACTIONS.get(node.subtype)
    if not spec:
        trace.append(_trace_node(node, decision="unknown_action"))
        return
    if dry_run:
        trace.append(_trace_node(node, decision="would_execute"))
    else:
        try:
            res = await spec.execute(node.params, event)
            actions_executed.append({"node_id": node.id, "subtype": node.subtype,
                                     "ok": res.ok, "detail": res.detail})
            trace.append(_trace_node(node, decision="executed",
                                     ok=res.ok, detail=res.detail))
        except Exception as e:
            logger.warning("Action %s crashed: %s", node.subtype, e)
            trace.append(_trace_node(node, decision="error", detail=str(e)))
    if node.subtype != "ignore":
        await _traverse(flow, node.id, "output", event, trace,
                        actions_executed, dry_run, depth + 1)


async def dispatch_event(event: TriggerEvent, *, owner: str | None = None,
                         dry_run: bool = False) -> list[dict]:
    """Iteriert alle Flows des Owners (oder alle wenn None) und ruft
    dispatch() pro Flow. Liefert die Trace-Resultate."""
    flows = bp.list_flows(owner=owner)
    out = []
    for flow in flows:
        if not flow.enabled:
            continue
        try:
            result = await dispatch(flow, event, dry_run=dry_run)
            if result["matched"]:
                out.append({"flow_id": flow.flow_id, "owner": flow.owner, **result})
        except Exception as e:
            logger.warning("Flow %s/%s crashed: %s", flow.owner, flow.flow_id, e)
    return out
