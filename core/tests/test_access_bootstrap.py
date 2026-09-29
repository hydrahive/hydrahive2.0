"""Übergang und Anfangs-Freigaben (Spec access-groups §11, §12, Plan Task 5.3).

Beim ersten Kennenlernen einer Funktion wird ihr Default angewendet:
'everyone' legt eine everyone-Freigabe an, 'admin_only' legt nichts an.
Danach fasst der Bootstrap diese Funktion nie wieder an. Was der Admin ändert
oder entfernt, bleibt so.
"""
from __future__ import annotations

import json

import pytest

from hydrahive.access import bootstrap, capabilities, grants, store
from hydrahive.modules.manifest import ModuleManifest
from tests._access_rows import _own_access_rows  # noqa: F401  (autouse)


@pytest.fixture
def cat(tmp_path, monkeypatch):
    c = capabilities.Catalog.with_core()
    monkeypatch.setattr(capabilities, "CATALOG", c)
    return c


def _module(cat, tmp_path, mid, caps):
    p = tmp_path / f"{mid}.json"
    p.write_text(json.dumps({"id": mid, "name": mid, "version": "1.0.0", "capabilities": caps}))
    cat.register_module(ModuleManifest.load(p))


def test_everyone_default_creates_grant(client, cat, tmp_path):
    _module(cat, tmp_path, "bsa", [{"id": "module.bsa", "label": "a", "default": "everyone"}])
    bootstrap.apply_defaults()
    assert grants.grants_for("module.bsa") == [
        {"capability": "module.bsa", "subject_type": "everyone", "subject_id": "", "level": "use"}]


def test_admin_only_default_creates_nothing(client, cat, tmp_path):
    _module(cat, tmp_path, "bsb", [{"id": "module.bsb", "label": "b", "default": "admin_only"}])
    bootstrap.apply_defaults()
    assert grants.grants_for("module.bsb") == []


def test_core_capabilities_are_admin_only(client, cat):
    bootstrap.apply_defaults()
    for cap in ("core.vms", "core.containers", "core.federation"):
        assert grants.grants_for(cap) == []


def test_idempotent(client, cat, tmp_path):
    _module(cat, tmp_path, "bsc", [{"id": "module.bsc", "label": "c", "default": "everyone"}])
    bootstrap.apply_defaults()
    bootstrap.apply_defaults()
    assert len(grants.grants_for("module.bsc")) == 1
    assert [e["action"] for e in store.audit_for("cap:module.bsc")] == ["bootstrap_default"]


def test_admin_revocation_survives_restart(client, cat, tmp_path):
    _module(cat, tmp_path, "bsd", [{"id": "module.bsd", "label": "d", "default": "everyone"}])
    bootstrap.apply_defaults()
    grants.revoke("module.bsd", "everyone", "", actor_id="adm")
    bootstrap.apply_defaults()
    assert grants.grants_for("module.bsd") == []


def test_new_module_later_gets_its_default(client, cat, tmp_path):
    bootstrap.apply_defaults()
    _module(cat, tmp_path, "bse", [{"id": "module.bse", "label": "e", "default": "everyone"}])
    bootstrap.apply_defaults()
    assert len(grants.grants_for("module.bse")) == 1


def test_notice_lists_admin_only_until_acknowledged(client, cat, tmp_path):
    _module(cat, tmp_path, "bsf", [{"id": "bsf.control", "label": "f", "default": "admin_only"}])
    bootstrap.apply_defaults()
    pending = bootstrap.pending_notice()
    assert "bsf.control" in pending and "core.vms" in pending
    bootstrap.acknowledge_notice(actor_id="adm")
    assert bootstrap.pending_notice() == []


def test_notice_ignores_admin_only_with_grant(client, cat, tmp_path):
    _module(cat, tmp_path, "bsg", [{"id": "bsg.control", "label": "g", "default": "admin_only"}])
    bootstrap.apply_defaults()
    grants.grant("bsg.control", "everyone", "", "use", actor_id="adm")
    assert "bsg.control" not in bootstrap.pending_notice()


def test_notice_routes(client, admin_headers, auth_headers, cat):
    bootstrap.apply_defaults()
    assert client.get("/api/access/notice", headers=auth_headers).status_code == 403
    data = client.get("/api/access/notice", headers=admin_headers).json()
    assert "core.vms" in data["pending"]
    assert client.post("/api/access/notice/ack", headers=admin_headers).status_code == 204
    assert client.get("/api/access/notice", headers=admin_headers).json()["pending"] == []
