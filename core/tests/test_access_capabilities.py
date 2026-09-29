"""Katalog der prüfbaren Funktionen (Spec access-groups §8, Plan Task 1.4).

Der Katalog lebt im Speicher. Jeder Test arbeitet auf einem frischen Katalog,
damit sich Tests nicht gegenseitig beeinflussen.
"""
from __future__ import annotations

import json

import pytest

from hydrahive.access.capabilities import Catalog
from hydrahive.modules.manifest import ModuleManifest


def _manifest(tmp_path, mid: str, caps=None) -> ModuleManifest:
    d = {"id": mid, "name": mid, "version": "1.0.0"}
    if caps is not None:
        d["capabilities"] = caps
    p = tmp_path / f"{mid}.json"
    p.write_text(json.dumps(d))
    return ModuleManifest.load(p)


@pytest.fixture
def cat():
    return Catalog.with_core()


def test_core_capabilities_known(cat):
    for cap in ("core.vms", "core.containers", "core.federation"):
        assert cat.is_declared(cap)
        assert cat.get(cap).default == "admin_only"


def test_module_without_capabilities_declares_nothing(cat, tmp_path):
    cat.register_module(_manifest(tmp_path, "plain"))
    assert not cat.is_declared("module.plain")


def test_module_capability_adds_base_automatically(cat, tmp_path):
    cat.register_module(_manifest(tmp_path, "ha", [
        {"id": "ha.control", "label": "Schalten", "default": "admin_only", "tools": ["ha_call_service"]},
    ]))
    assert cat.is_declared("module.ha")
    assert cat.get("module.ha").default == "everyone"
    assert cat.get("ha.control").module_id == "ha"


def test_explicit_base_capability_is_kept(cat, tmp_path):
    cat.register_module(_manifest(tmp_path, "voice", [
        {"id": "module.voice", "label": "Voice", "default": "admin_only"},
    ]))
    assert cat.get("module.voice").default == "admin_only"


def test_tool_mapping_explicit_and_fallback(cat, tmp_path):
    cat.register_module(_manifest(tmp_path, "ha", [
        {"id": "ha.control", "label": "Schalten", "tools": ["ha_call_service"]},
    ]))
    assert cat.capability_for_tool("ha_call_service", module_id="ha") == "ha.control"
    assert cat.capability_for_tool("ha_list_entities", module_id="ha") == "module.ha"


def test_tool_of_undeclared_module_has_no_capability(cat, tmp_path):
    cat.register_module(_manifest(tmp_path, "plain"))
    assert cat.capability_for_tool("plain_tool", module_id="plain") is None


def test_core_tool_has_no_capability_unless_mapped(cat):
    assert cat.capability_for_tool("shell_exec", module_id="") is None


def test_core_tool_mapping_for_federation(cat):
    # ask_agent routet persona@workstation an die Föderation. Die Prüfung sitzt im
    # Werkzeug selbst (Plan Task 3.4), nicht in der Zuordnung Werkzeug → Funktion.
    assert cat.capability_for_tool("ask_agent", module_id="") is None


def test_unregister_module(cat, tmp_path):
    cat.register_module(_manifest(tmp_path, "ha", [{"id": "ha.control", "label": "x"}]))
    cat.unregister_module("ha")
    assert not cat.is_declared("ha.control") and not cat.is_declared("module.ha")


def test_listing_is_grouped(cat, tmp_path):
    cat.register_module(_manifest(tmp_path, "ha", [{"id": "ha.control", "label": "x"}]))
    ids = [c.id for c in cat.all()]
    assert ids.index("core.vms") < ids.index("module.ha") < ids.index("ha.control")
