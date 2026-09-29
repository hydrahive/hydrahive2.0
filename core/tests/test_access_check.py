"""Prüfung „darf dieser Nutzer diese Funktion?“ (Spec access-groups §7, Plan Task 1.5)."""
from __future__ import annotations

import json

import pytest

from hydrahive.access import capabilities as capabilities_mod
from hydrahive.access import check, grants, store
from hydrahive.access.capabilities import Catalog
from hydrahive.modules.manifest import ModuleManifest


@pytest.fixture
def cat(tmp_path, monkeypatch):
    c = Catalog.with_core()
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"id": "chk", "name": "Chk", "version": "1.0.0", "capabilities": [
        {"id": "module.chk", "label": "Chk", "default": "admin_only"},
        {"id": "chk.control", "label": "Steuern", "default": "admin_only", "tools": ["chk_do"]},
    ]}))
    c.register_module(ModuleManifest.load(p))
    monkeypatch.setattr(capabilities_mod, "CATALOG", c)
    return c


def test_admin_may_everything(client, cat):
    assert check.level(user_id="adm", role="admin", capability="chk.control") == "manage"


def test_undeclared_capability_is_open(client, cat):
    assert check.can_use(user_id="u-1", role="user", capability="module.gibtsnicht")


def test_declared_without_grant_is_denied(client, cat):
    assert not check.can_use(user_id="u-none", role="user", capability="chk.control")


def test_everyone_grant(client, cat):
    grants.grant("module.chk", "everyone", "", "use", actor_id="adm")
    assert check.can_use(user_id="u-any", role="user", capability="module.chk")


def test_direct_user_grant(client, cat):
    grants.grant("chk.control", "user", "u-direct", "use", actor_id="adm")
    assert check.can_use(user_id="u-direct", role="user", capability="chk.control")
    assert not check.can_use(user_id="u-other", role="user", capability="chk.control")


def test_group_grant_applies_only_to_members(client, cat):
    g = store.create_group("Chk-Familie", "", actor_id="adm")
    store.add_member(g["id"], "u-member", actor_id="adm")
    grants.grant("chk.control", "group", g["id"], "use", actor_id="adm")
    assert check.can_use(user_id="u-member", role="user", capability="chk.control")
    assert not check.can_use(user_id="u-outside", role="user", capability="chk.control")


def test_highest_level_wins(client, cat):
    g = store.create_group("Chk-Stufen", "", actor_id="adm")
    store.add_member(g["id"], "u-lvl", actor_id="adm")
    grants.grant("chk.control", "group", g["id"], "use", actor_id="adm")
    grants.grant("chk.control", "user", "u-lvl", "manage", actor_id="adm")
    assert check.level(user_id="u-lvl", role="user", capability="chk.control") == "manage"
    assert check.can_manage(user_id="u-lvl", role="user", capability="chk.control")


def test_use_does_not_imply_manage(client, cat):
    grants.grant("chk.control", "user", "u-use", "use", actor_id="adm")
    assert not check.can_manage(user_id="u-use", role="user", capability="chk.control")


def test_store_error_fails_closed(client, cat, monkeypatch, caplog):
    def boom(**_kw):
        raise RuntimeError("db kaputt")
    monkeypatch.setattr(check.grants, "grants_matching", boom)
    assert not check.can_use(user_id="u-err", role="user", capability="chk.control")
    assert "fail-closed" in caplog.text


def test_capabilities_for_user(client, cat):
    grants.grant("module.chk", "user", "u-list", "use", actor_id="adm")
    caps = check.capabilities_for(user_id="u-list", role="user")
    assert caps == {"module.chk": "use"}


def test_capabilities_for_admin_is_all_declared(client, cat):
    caps = check.capabilities_for(user_id="adm", role="admin")
    assert caps["chk.control"] == "manage" and caps["core.vms"] == "manage"


def test_resolve_user_id_from_username(client, cat):
    uid = check.user_id_for("testuser")
    assert uid and uid != "testuser"
    assert check.user_id_for("gibt-es-nicht") is None
