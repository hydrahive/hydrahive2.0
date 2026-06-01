"""Sicherheits-Tests für eingehende AgentLink-Handoffs (Issue #177).

Kern: ein eingehender Handoff darf NIEMALS auf den unrestricted Admin-Master
eskalieren. Nur explizit adressierte, bekannte, aktive Agenten dürfen laufen.
Zusätzlich: ausgehende AgentLink-Calls tragen den Shared-Token wenn gesetzt.
"""
from __future__ import annotations

import logging

import pytest

from hydrahive.agentlink import client
from hydrahive.runner.handoff_receiver import _find_target_agent, _warn_if_unconfirmed


# --- _find_target_agent: keine Master-Eskalation ---------------------------

def test_returns_addressed_active_agent(monkeypatch):
    agent = {"id": "spec-1", "status": "active", "type": "specialist"}
    monkeypatch.setattr("hydrahive.agents.config.get", lambda _id: agent)
    assert _find_target_agent("spec-1") == agent


def test_unaddressed_handoff_is_rejected(monkeypatch):
    # Kein to_agent → KEIN Fallback auf Admin-Master, sondern None.
    called = {"list_by_owner": False}

    def _fail_list(_owner):
        called["list_by_owner"] = True
        return [{"id": "master", "type": "master", "status": "active"}]

    monkeypatch.setattr("hydrahive.agents.config.list_by_owner", _fail_list)
    assert _find_target_agent(None) is None
    assert called["list_by_owner"] is False, "Master-Fallback darf gar nicht erst aufgerufen werden"


def test_unknown_agent_is_rejected(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get", lambda _id: None)
    assert _find_target_agent("does-not-exist") is None


def test_inactive_agent_is_rejected(monkeypatch):
    agent = {"id": "spec-2", "status": "disabled", "type": "specialist"}
    monkeypatch.setattr("hydrahive.agents.config.get", lambda _id: agent)
    assert _find_target_agent("spec-2") is None


# --- _warn_if_unconfirmed: Sichtbarkeit für auto-exec ----------------------

def test_warns_when_target_auto_executes(caplog):
    target = {"id": "spec-3", "require_tool_confirm": False}
    with caplog.at_level(logging.WARNING):
        _warn_if_unconfirmed(target)
    assert any("require_tool_confirm=False" in r.message for r in caplog.records)


def test_no_warning_when_target_requires_confirm(caplog):
    target = {"id": "spec-4", "require_tool_confirm": True}
    with caplog.at_level(logging.WARNING):
        _warn_if_unconfirmed(target)
    assert not caplog.records


# --- ausgehende Calls: Shared-Token-Auth -----------------------------------

def _fake_settings(token: str):
    return type("S", (), {"agentlink_token": token})()


def test_auth_headers_empty_without_token(monkeypatch):
    monkeypatch.setattr(client, "settings", _fake_settings(""))
    assert client._auth_headers() == {}


def test_auth_headers_carry_bearer_when_set(monkeypatch):
    monkeypatch.setattr(client, "settings", _fake_settings("s3cr3t"))
    assert client._auth_headers() == {"Authorization": "Bearer s3cr3t"}
