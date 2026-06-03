"""Per-Agent tool_config (Schicht 2: Postfach pro Buddy) — Backend-Mechanik.

tool_config liegt persistent am Agent, fließt in ctx.config und füttert so die
schon gebauten smtp/imap-Overrides in send_mail/read_mail. Secrets werden in
API-Antworten maskiert (Muster wie system_settings: leeres Passwort = behalten).
Lazy imports wegen settings.data_dir-Freeze.
"""
from __future__ import annotations

import pytest

MODEL = "claude-3-7-sonnet-20250219"


# ---------------------------------------------------------------- Validierung

def test_validate_accepts_smtp_and_imap():
    from hydrahive.agents import _validation
    _validation.validate_tool_config({
        "smtp": {"host": "h", "from": "a@b", "user": "u", "password": "x",
                 "port": 465, "use_tls": True},
        "imap": {"host": "h", "user": "u", "password": "x", "port": 993},
    })


def test_validate_rejects_unknown_top_key():
    from hydrahive.agents import _validation, AgentValidationError
    with pytest.raises(AgentValidationError):
        _validation.validate_tool_config({"ftp": {}})


def test_validate_rejects_unknown_block_key():
    from hydrahive.agents import _validation, AgentValidationError
    with pytest.raises(AgentValidationError):
        _validation.validate_tool_config({"smtp": {"hostt": "h"}})


def test_validate_rejects_non_int_port():
    from hydrahive.agents import _validation, AgentValidationError
    with pytest.raises(AgentValidationError):
        _validation.validate_tool_config({"smtp": {"port": "abc"}})


def test_validate_rejects_non_dict():
    from hydrahive.agents import _validation, AgentValidationError
    with pytest.raises(AgentValidationError):
        _validation.validate_tool_config(["nope"])


# ---------------------------------------------------------------- Maskierung

def test_mask_hides_password_adds_flag():
    from hydrahive.agents import _tool_config
    masked = _tool_config.mask({"smtp": {"host": "h", "password": "secret"}})
    assert masked["smtp"]["password"] == ""
    assert masked["smtp"]["password_set"] is True


def test_mask_flag_false_when_no_password():
    from hydrahive.agents import _tool_config
    masked = _tool_config.mask({"imap": {"host": "h", "password": ""}})
    assert masked["imap"]["password_set"] is False


def test_mask_none_passthrough():
    from hydrahive.agents import _tool_config
    assert _tool_config.mask(None) is None


def test_mask_does_not_mutate_input():
    from hydrahive.agents import _tool_config
    src = {"smtp": {"password": "secret"}}
    _tool_config.mask(src)
    assert src["smtp"]["password"] == "secret"   # Original unangetastet


# ---------------------------------------------------------------- Secret-Merge

def test_merge_preserves_existing_password_on_empty():
    from hydrahive.agents import _tool_config
    merged = _tool_config.merge_secrets(
        {"smtp": {"password": "old"}},
        {"smtp": {"host": "h", "password": ""}})
    assert merged["smtp"]["password"] == "old"


def test_merge_takes_new_password():
    from hydrahive.agents import _tool_config
    merged = _tool_config.merge_secrets(
        {"smtp": {"password": "old"}},
        {"smtp": {"host": "h", "password": "new"}})
    assert merged["smtp"]["password"] == "new"


def test_merge_strips_password_set_flag():
    from hydrahive.agents import _tool_config
    merged = _tool_config.merge_secrets({}, {"smtp": {"password": "x", "password_set": True}})
    assert "password_set" not in merged["smtp"]


# ---------------------------------------------------------------- Runner-Wiring

def test_effective_tool_config_uses_agent_persisted():
    from hydrahive.runner._run_workspace import effective_tool_config
    agent = {"tool_config": {"smtp": {"host": "agent.host", "from": "a@b"}}}
    eff = effective_tool_config(agent, None)
    assert eff["smtp"]["host"] == "agent.host"


def test_effective_tool_config_run_param_overrides_agent():
    from hydrahive.runner._run_workspace import effective_tool_config
    agent = {"tool_config": {"project_id": "p1"}}
    eff = effective_tool_config(agent, {"project_id": "p2"})
    assert eff["project_id"] == "p2"


def test_effective_tool_config_empty_when_none():
    from hydrahive.runner._run_workspace import effective_tool_config
    assert effective_tool_config({}, None) == {}


# ---------------------------------------------------------------- Update-Roundtrip

def test_update_persists_and_preserves_secret(client):
    from hydrahive.agents import config as agent_config
    a = agent_config.create(agent_type="master", name="mailbuddy", llm_model=MODEL,
                            owner="till", temperature=0.7, max_tokens=1000, thinking_budget=0)
    try:
        agent_config.update(a["id"], tool_config={
            "smtp": {"host": "h1", "from": "a@b", "user": "u", "password": "sekret"}})
        assert agent_config.get(a["id"])["tool_config"]["smtp"]["password"] == "sekret"

        # leeres Passwort = behalten, Rest aktualisieren
        agent_config.update(a["id"], tool_config={
            "smtp": {"host": "h2", "from": "a@b", "user": "u", "password": ""}})
        stored = agent_config.get(a["id"])["tool_config"]["smtp"]
        assert stored["host"] == "h2"
        assert stored["password"] == "sekret"
    finally:
        agent_config.delete(a["id"])


def test_api_get_agent_masks_password(client, admin_headers):
    from hydrahive.agents import config as agent_config
    a = agent_config.create(agent_type="master", name="apimask", llm_model=MODEL,
                            owner="admin", temperature=0.7, max_tokens=1000, thinking_budget=0)
    try:
        agent_config.update(a["id"], tool_config={
            "smtp": {"host": "h", "from": "a@b", "user": "u", "password": "topsecret"}})
        r = client.get(f"/api/agents/{a['id']}", headers=admin_headers)
        assert r.status_code == 200
        smtp = r.json()["tool_config"]["smtp"]
        assert smtp["password"] == ""
        assert smtp["password_set"] is True
        assert "topsecret" not in r.text          # Secret verlässt die API nie roh
    finally:
        agent_config.delete(a["id"])
