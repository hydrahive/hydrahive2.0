"""F2 — Modul-Butler-Brücke: ctx.register_butler_* + Registry-Einspeisung.

Module bringen eigene Trigger/Conditions/Actions mit (SPEC: „weitere Trigger/
Conditions/Actions als Plugin nachrüstbar"). Die Brücke schiebt sie nach
load_builtins() in die bestehende Butler-Registry — ohne Core-Builtins zu
überschreiben.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import hydrahive.butler.registry as reg
from hydrahive.butler.registry import (
    ActionResult,
    ActionSpec,
    ConditionSpec,
    TriggerSpec,
)
from hydrahive.modules import butler_bridge
from hydrahive.modules.context import ModuleContext
from hydrahive.modules.manifest import ModuleManifest
from hydrahive.modules.registry import LoadedModule


def _trigger(subtype: str) -> TriggerSpec:
    return TriggerSpec(subtype=subtype, label="L", description="D", params=[], matches=lambda p, e: True)


def _condition(subtype: str) -> ConditionSpec:
    return ConditionSpec(subtype=subtype, label="L", description="D", params=[], evaluate=lambda p, e: True)


def _action(subtype: str) -> ActionSpec:
    return ActionSpec(subtype=subtype, label="L", description="D", params=[], execute=lambda p, e: ActionResult(ok=True))


def _loaded(mid: str, ctx: ModuleContext) -> LoadedModule:
    return LoadedModule(
        name=mid, manifest=ModuleManifest(id=mid, name=mid, version="1.0.0"),
        path=Path("."), ctx=ctx, loaded=True,
    )


@pytest.fixture
def restore_butler_registry():
    snap = (dict(reg.TRIGGERS), dict(reg.CONDITIONS), dict(reg.ACTIONS))
    yield
    reg.TRIGGERS.clear(); reg.TRIGGERS.update(snap[0])
    reg.CONDITIONS.clear(); reg.CONDITIONS.update(snap[1])
    reg.ACTIONS.clear(); reg.ACTIONS.update(snap[2])


def test_register_butler_specs_speichern():
    ctx = ModuleContext("demo")
    ctx.register_butler_trigger(_trigger("crypto_threshold"))
    ctx.register_butler_condition(_condition("crypto_above"))
    ctx.register_butler_action(_action("crypto_notify"))
    assert [s.subtype for s in ctx.butler_triggers] == ["crypto_threshold"]
    assert [s.subtype for s in ctx.butler_conditions] == ["crypto_above"]
    assert [s.subtype for s in ctx.butler_actions] == ["crypto_notify"]


def test_bridge_speist_in_registry_ein(monkeypatch, restore_butler_registry):
    ctx = ModuleContext("demo")
    ctx.register_butler_trigger(_trigger("test_modbridge_trig"))
    ctx.register_butler_condition(_condition("test_modbridge_cond"))
    ctx.register_butler_action(_action("test_modbridge_act"))
    monkeypatch.setattr(butler_bridge, "REGISTRY", {"demo": _loaded("demo", ctx)})

    n = butler_bridge.register_module_butler_subtypes()
    assert n == 3
    assert "test_modbridge_trig" in reg.TRIGGERS
    assert "test_modbridge_cond" in reg.CONDITIONS
    assert "test_modbridge_act" in reg.ACTIONS


def test_bridge_schuetzt_core_builtins(monkeypatch, restore_butler_registry):
    reg.load_builtins()
    original = reg.TRIGGERS.get("cron_fired")
    assert original is not None  # Builtin vorhanden

    ctx = ModuleContext("evil")
    ctx.register_butler_trigger(_trigger("cron_fired"))  # versucht Builtin zu kapern
    monkeypatch.setattr(butler_bridge, "REGISTRY", {"evil": _loaded("evil", ctx)})

    n = butler_bridge.register_module_butler_subtypes()
    assert n == 0  # Kollision → nichts registriert
    assert reg.TRIGGERS["cron_fired"] is original  # Builtin unangetastet


def test_bridge_ueberspringt_nicht_geladene_module(monkeypatch, restore_butler_registry):
    ctx = ModuleContext("ok")
    ctx.register_butler_trigger(_trigger("test_ok_trig"))
    broken = LoadedModule(name="broken", manifest=None, path=Path("."), ctx=None, loaded=False, error="x")
    monkeypatch.setattr(butler_bridge, "REGISTRY", {"ok": _loaded("ok", ctx), "broken": broken})

    n = butler_bridge.register_module_butler_subtypes()
    assert n == 1
    assert "test_ok_trig" in reg.TRIGGERS
