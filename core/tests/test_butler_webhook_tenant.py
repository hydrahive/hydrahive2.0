"""Tenant-Isolation für den Projekt-Webhook (Issue #178).

Ein eingehender Projekt-Webhook darf NUR Flows feuern, die
  (a) einem auf dem Projekt autorisierten Owner gehören (created_by + members),
  (b) explizit auf DIESES Projekt gescopt sind (scope==project, scope_id==id),
  (c) enabled sind.
Insbesondere darf ein fremder User seinen Flow NICHT durch ein gefälschtes
scope_id auf ein fremdes Projekt feuern.
"""
from __future__ import annotations

from hydrahive.api.routes.butler import _project_flows
from hydrahive.butler.models import Flow


def _flow(owner: str, *, enabled: bool, scope: str, scope_id: str | None, fid: str) -> Flow:
    return Flow(
        flow_id=fid,
        name="F",
        owner=owner,
        enabled=enabled,
        scope=scope,
        scope_id=scope_id,
        nodes=[
            {"id": "t1", "type": "trigger", "subtype": "webhook_received",
             "position": {"x": 0, "y": 0}, "params": {}},
            {"id": "a1", "type": "action", "subtype": "ignore",
             "position": {"x": 200, "y": 0}, "params": {}},
        ],
        edges=[{"id": "e1", "source": "t1", "target": "a1", "source_handle": "output"}],
    )


def _patch_flows(monkeypatch, by_owner: dict[str, list[Flow]]):
    monkeypatch.setattr(
        "hydrahive.api.routes.butler.bp.list_flows",
        lambda owner=None: list(by_owner.get(owner, [])),
    )


PROJECT = {"id": "projX", "created_by": "alice", "members": ["bob"]}


def test_selects_owner_enabled_project_scoped_flow(monkeypatch):
    f = _flow("alice", enabled=True, scope="project", scope_id="projX", fid="a-ok")
    _patch_flows(monkeypatch, {"alice": [f], "bob": []})
    assert [x.flow_id for x in _project_flows(PROJECT, "projX")] == ["a-ok"]


def test_includes_member_flows(monkeypatch):
    fa = _flow("alice", enabled=True, scope="project", scope_id="projX", fid="a")
    fb = _flow("bob", enabled=True, scope="project", scope_id="projX", fid="b")
    _patch_flows(monkeypatch, {"alice": [fa], "bob": [fb]})
    assert {x.flow_id for x in _project_flows(PROJECT, "projX")} == {"a", "b"}


def test_excludes_disabled(monkeypatch):
    f = _flow("alice", enabled=False, scope="project", scope_id="projX", fid="off")
    _patch_flows(monkeypatch, {"alice": [f], "bob": []})
    assert _project_flows(PROJECT, "projX") == []


def test_excludes_user_scoped(monkeypatch):
    f = _flow("alice", enabled=True, scope="user", scope_id=None, fid="usr")
    _patch_flows(monkeypatch, {"alice": [f], "bob": []})
    assert _project_flows(PROJECT, "projX") == []


def test_excludes_other_project(monkeypatch):
    f = _flow("alice", enabled=True, scope="project", scope_id="projY", fid="other")
    _patch_flows(monkeypatch, {"alice": [f], "bob": []})
    assert _project_flows(PROJECT, "projX") == []


def test_forged_scope_id_by_outsider_does_not_fire(monkeypatch):
    # mallory ist NICHT auf dem Projekt — ihr Flow zeigt zwar auf projX,
    # darf aber niemals geladen/gefeuert werden (Kern des cross-tenant-Bypass).
    evil = _flow("mallory", enabled=True, scope="project", scope_id="projX", fid="evil")
    _patch_flows(monkeypatch, {"alice": [], "bob": [], "mallory": [evil]})
    assert _project_flows(PROJECT, "projX") == []
