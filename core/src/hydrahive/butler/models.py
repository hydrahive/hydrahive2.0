"""Pydantic-Models für Butler-Flows.

Validierungs-Regeln (in `Flow.validate_graph`):
- genau ein Trigger-Node
- jeder Edge zeigt auf existierende Nodes
- Condition-Edges nutzen nur `true`/`false` als sourceHandle
- Action-/Trigger-Edges nutzen nur `output`
- keine Zyklen (DFS-Cycle-Check)
- kein Orphan-Action-Node (jeder Action muss vom Trigger erreichbar sein)
"""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

NodeType = Literal["trigger", "condition", "action"]
Scope = Literal["user", "project"]
NAME_RE = re.compile(r"^[A-Za-z0-9_\- ]{1,80}$")


class NodePosition(BaseModel):
    x: float
    y: float


class Node(BaseModel):
    """Graph-Node. `subtype` entscheidet welche Param-Schema gelten —
    konkrete Validierung der `params` macht der Registry-Eintrag."""
    id: str = Field(min_length=1, max_length=80)
    type: NodeType
    subtype: str = Field(min_length=1, max_length=80)
    position: NodePosition
    params: dict[str, Any] = Field(default_factory=dict)
    label: str | None = Field(default=None, max_length=120)


class Edge(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    source: str
    target: str
    source_handle: Literal["output", "true", "false"] = "output"


class Flow(BaseModel):
    flow_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=80)
    owner: str = Field(min_length=1, max_length=80)
    enabled: bool = False
    scope: Scope = "user"
    scope_id: str | None = None
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    created_at: str | None = None
    modified_at: str | None = None
    modified_by: str | None = None

    @field_validator("name")
    @classmethod
    def _name_format(cls, v: str) -> str:
        if not NAME_RE.match(v):
            raise ValueError("name_invalid_chars")
        return v

    @model_validator(mode="after")
    def validate_graph(self) -> "Flow":
        node_ids = {n.id for n in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("duplicate_node_id")

        triggers = [n for n in self.nodes if n.type == "trigger"]
        if len(triggers) > 1:
            raise ValueError("multiple_triggers")

        for e in self.edges:
            if e.source not in node_ids or e.target not in node_ids:
                raise ValueError("edge_endpoint_unknown")
            src = next(n for n in self.nodes if n.id == e.source)
            if src.type == "condition" and e.source_handle not in ("true", "false"):
                raise ValueError("condition_handle_invalid")
            if src.type != "condition" and e.source_handle != "output":
                raise ValueError("non_condition_handle_invalid")

        if self.nodes and self.edges:
            self._check_no_cycles()
            if triggers:
                self._check_actions_reachable(triggers[0].id)

        return self

    def _check_no_cycles(self) -> None:
        adj: dict[str, list[str]] = {n.id: [] for n in self.nodes}
        for e in self.edges:
            adj[e.source].append(e.target)
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n.id: WHITE for n in self.nodes}

        def dfs(u: str) -> None:
            color[u] = GRAY
            for v in adj[u]:
                if color[v] == GRAY:
                    raise ValueError("cycle_detected")
                if color[v] == WHITE:
                    dfs(v)
            color[u] = BLACK

        for n in self.nodes:
            if color[n.id] == WHITE:
                dfs(n.id)

    def _check_actions_reachable(self, trigger_id: str) -> None:
        adj: dict[str, list[str]] = {n.id: [] for n in self.nodes}
        for e in self.edges:
            adj[e.source].append(e.target)
        seen = {trigger_id}
        stack = [trigger_id]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        for n in self.nodes:
            if n.type == "action" and n.id not in seen:
                raise ValueError("orphan_action")


class TriggerEvent(BaseModel):
    """Was die Channel-Adapter / Webhooks an `butler.dispatch()` reichen."""
    event_type: str
    channel: str | None = None
    contact_id: str | None = None
    contact_label: str | None = None
    is_known: bool = False
    message_text: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str | None = None
    owner: str | None = None
