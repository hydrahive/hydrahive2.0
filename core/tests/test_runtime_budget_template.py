"""Budget bei Delegation aus dem Template des Ziels, Überschreitung (Plan E4 T1–T3).

Spec agent-templates.md Kap. 7: Ziel mit Template bekommt dessen Budget – nicht mehr min(Agent, Profil standard).
Überschreitung nur mit Begründung, höchstens um `overrun_pct`, gekappt an den Validierungsgrenzen.
Ungebundene Ziele (Altbestand) verhalten sich wie bisher.
"""
from __future__ import annotations

import pytest

from hydrahive.agentlink.runtime_profiles import (
    OVERRUN_PROFILE,
    RUNTIME_METADATA_KEY,
    effective_budget,
    profile_from_reason,
    reason_with_profile,
    session_budget,
)
from hydrahive.agents import templates as tpl
from hydrahive.agents.templates import _store

KNOWN = {"claude-opus-5-5", "claude-sonnet-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"}


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(_store, "_path", lambda: tmp_path / "agent_templates.json")
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: KNOWN)
    monkeypatch.setattr(tpl._defaults, "_current_system_models", lambda: {})
    _store.reset_cache()
    yield
    _store.reset_cache()


def bound(template="reviewer", **extra):
    return {"template": template, "max_iterations": 5, "max_tokens": 100, "handoff_timeout_seconds": 60, **extra}


def test_template_budget_statt_standard_profil():
    b = effective_budget(bound(), "standard")
    assert (b.max_iterations, b.max_tokens, b.timeout_seconds) == (96, 32_768, 1_800)
    assert b.profile == "template"


@pytest.mark.parametrize("profile", ["quick", "deep", "unbekannt"])
def test_profil_spielt_bei_gebundenen_keine_rolle(profile):
    b = effective_budget(bound(), profile)
    assert b.max_iterations == 96


def test_ueberschreitung_20_prozent():
    b = effective_budget(bound(), OVERRUN_PROFILE)
    assert (b.max_iterations, b.max_tokens, b.timeout_seconds) == (115, 39_321, 2_160)
    assert b.profile == OVERRUN_PROFILE


def test_ueberschreitung_gekappt():
    t = tpl.get("reviewer")
    t["budget"] = {**t["budget"], "max_iterations": 240, "max_tokens": 190_000, "timeout_seconds": 3_500,
                   "overrun_pct": 50}
    tpl.save("reviewer", t, by="admin")
    b = effective_budget(bound(), OVERRUN_PROFILE)
    assert (b.max_iterations, b.max_tokens, b.timeout_seconds) == (250, 200_000, 3_600)


def test_ueberschreitung_aus():
    t = tpl.get("reviewer")
    t["budget"] = {**t["budget"], "overrun_pct": 0}
    tpl.save("reviewer", t, by="admin")
    assert effective_budget(bound(), OVERRUN_PROFILE).max_iterations == 96


def test_ungebunden_wie_bisher():
    agent = {"max_iterations": 120, "max_tokens": 64_000, "handoff_timeout_seconds": 2_400}
    b = effective_budget(agent, "standard")
    assert (b.max_iterations, b.max_tokens, b.timeout_seconds) == (32, 16_384, 540)
    b = effective_budget(agent, OVERRUN_PROFILE)          # ohne Template gibt es keine Überschreitung
    assert (b.max_iterations, b.profile) == (32, "standard")


def test_umschlag_overrun():
    reason = reason_with_profile("spec-1", OVERRUN_PROFILE, "review")
    assert profile_from_reason(reason) == OVERRUN_PROFILE


def test_sitzung_mit_gespeichertem_budget():
    meta = {RUNTIME_METADATA_KEY: effective_budget(bound(), OVERRUN_PROFILE).as_metadata()}
    assert session_budget(bound(), meta).max_iterations == 115
