from __future__ import annotations

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.agents import external_instances as ei
from hydrahive.api.middleware import api_keys, users

MODEL = "claude-3-7-sonnet-20250219"


@pytest.fixture(autouse=True)
def _cleanup_external(client):
    # client → init_db + Env; nach jedem Test angelegte Instanzen entfernen,
    # damit der session-scoped Config-Dir andere Tests nicht verschmutzt.
    yield
    for inst in ei.list_instances():
        ei.delete_instance(inst["agent_id"])


def test_create_instance_makes_user_agent_key():
    res = ei.create_instance("joshua-test", MODEL)
    assert res["username"] == "joshua-test"
    assert res["api_key"].startswith("hhk_")
    agent = agent_config.get(res["agent_id"])
    assert agent["external"] is True
    assert agent["owner"] == "joshua-test"
    assert any(u["username"] == "joshua-test" for u in users.list_users())
    assert len(api_keys.list_keys(username="joshua-test")) == 1


def test_list_instances_only_external():
    ei.create_instance("ext-1", MODEL)
    names = [i["name"] for i in ei.list_instances()]
    assert "ext-1" in names
    assert "Test Agent" not in names  # conftest-Agent ist nicht external


def test_delete_instance_removes_everything():
    res = ei.create_instance("gone", MODEL)
    assert ei.delete_instance(res["agent_id"]) is True
    assert agent_config.get(res["agent_id"]) is None
    assert not any(u["username"] == "gone" for u in users.list_users())
    assert api_keys.list_keys(username="gone") == []


def test_rotate_key_replaces():
    res = ei.create_instance("rot", MODEL)
    old = api_keys.list_keys(username="rot")[0]["id"]
    new_key = ei.rotate_key(res["agent_id"])
    assert new_key.startswith("hhk_")
    keys = api_keys.list_keys(username="rot")
    assert len(keys) == 1 and keys[0]["id"] != old


def test_create_duplicate_name_raises():
    ei.create_instance("dup", MODEL)
    with pytest.raises(ValueError):
        ei.create_instance("dup", MODEL)


def test_delete_instance_keeps_shared_owner():
    # external-Agent, dessen Owner ein bestehender (geteilter) User ist — wie er
    # via generische Agent-Route mit owner=admin entstünde. delete_instance darf
    # diesen User NICHT mitlöschen.
    agent = agent_config.create(
        agent_type="master", name="adm-ext", llm_model=MODEL, owner="admin",
        external=True, temperature=0.7, max_tokens=4096, thinking_budget=0,
    )
    assert ei.delete_instance(agent["id"]) is True
    assert agent_config.get(agent["id"]) is None
    assert any(u["username"] == "admin" for u in users.list_users())  # admin überlebt
