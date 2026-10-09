"""Schutzstufen normal/privat/gesundheit (docs/specs/knowledge-spaces.md §2.1, E1a)."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from hydrahive.db._mirror_levels import CORE_SENSITIVE, hidden_tools, rank, sensitive_tools
from hydrahive.db._mirror_scope import Scope, scope_for, where
from hydrahive.modules._manifest_sensitive import parse_sensitive_tools
from hydrahive.modules.manifest import ManifestError, ModuleManifest


# ── Stufen ────────────────────────────────────────────────────────────────────

def test_kernliste_nach_tills_entscheidung():
    assert CORE_SENSITIVE["query_fhir_data"] == CORE_SENSITIVE["query_health_data"] == "gesundheit"
    assert CORE_SENSITIVE["read_mail"] == CORE_SENSITIVE["send_mail"] == CORE_SENSITIVE["query_portfolio"] == "privat"
    assert "query_crypto_price" not in CORE_SENSITIVE  # öffentliche Kurse bleiben normal


def test_normal_sieht_weder_privat_noch_gesundheit():
    hidden = hidden_tools("normal")
    assert {"read_mail", "query_portfolio", "query_health_data"} <= set(hidden)


def test_privat_sieht_privat_aber_keine_gesundheit():
    hidden = hidden_tools("privat")
    assert "read_mail" not in hidden and "query_portfolio" not in hidden
    assert {"query_fhir_data", "query_health_data"} <= set(hidden)


def test_gesundheit_sieht_alles_und_unbekannt_ist_normal():
    assert hidden_tools("gesundheit") == []
    assert rank("quatsch") == 0 and hidden_tools("quatsch") == hidden_tools("normal")


def _mod(tools, loaded=True):
    return SimpleNamespace(loaded=loaded, manifest=SimpleNamespace(sensitive_tools=tuple(tools.items())))


def test_module_melden_eigene_werkzeuge_hoehere_stufe_gewinnt():
    reg = {"hb": _mod({"hb_query": "privat", "read_mail": "gesundheit"}), "kaputt": _mod({"x": "gesundheit"}, loaded=False)}
    with patch("hydrahive.modules.registry.REGISTRY", reg):
        st = sensitive_tools()
    assert st["hb_query"] == "privat"
    assert st["read_mail"] == "gesundheit"       # Modul stuft höher als Kern
    assert "x" not in st                          # nicht geladenes Modul zählt nicht


def test_modul_kann_kern_nicht_herabstufen():
    with patch("hydrahive.modules.registry.REGISTRY", {"m": _mod({"query_fhir_data": "privat"})}):
        assert sensitive_tools()["query_fhir_data"] == "gesundheit"


# ── Sicht je Agent ────────────────────────────────────────────────────────────

def test_e0_feld_sensitive_wird_weiter_verstanden():
    a = {"type": "project", "knowledge_access": {"sensitive": True}}
    assert scope_for(a, username="t", project_id="P").max_level == "gesundheit"
    b = {"type": "master", "knowledge_access": {"sensitive": False}}
    assert scope_for(b, username="t", project_id=None).max_level == "normal"


def test_max_level_gewinnt_und_unbekannt_ist_streng():
    a = {"type": "master", "knowledge_access": {"max_level": "privat", "sensitive": True}}
    assert scope_for(a, username="t", project_id=None).max_level == "privat"
    b = {"type": "master", "knowledge_access": {"max_level": "alles"}}
    assert scope_for(b, username="t", project_id=None).max_level == "normal"


def test_standard_buddy_gesundheit_projekt_normal():
    assert scope_for({"type": "master"}, username="t", project_id=None).max_level == "gesundheit"
    assert scope_for({"type": "project"}, username="t", project_id="P").max_level == "normal"


def test_filter_enthaelt_die_versteckten_werkzeuge_der_stufe():
    _, params, _ = where(Scope(username="t", projects=("P",), max_level="privat"), 1)
    assert params[-1] == hidden_tools("privat")
    conds, params, _ = where(Scope(username="t", scope="user", max_level="gesundheit"), 1)
    assert not any("s.tool_name" in c for c in conds) and params == ["t"]


# ── Manifest ──────────────────────────────────────────────────────────────────

def test_manifest_liest_sensitive_tools(tmp_path: Path):
    p = tmp_path / "manifest.json"
    p.write_text('{"id": "hb", "name": "HB", "version": "1", "sensitive_tools": {"b": "privat", "a": "gesundheit"}}')
    assert ModuleManifest.load(p).sensitive_tools == (("a", "gesundheit"), ("b", "privat"))


@pytest.mark.parametrize("bad", [["a"], {"a": "normal"}, {"a": "geheim"}, {"a b": "privat"}, {"": "privat"}])
def test_manifest_lehnt_ungueltiges_ab(bad):
    with pytest.raises(ManifestError):
        parse_sensitive_tools(bad, ManifestError)


def test_manifest_ohne_feld_ist_leer(tmp_path: Path):
    p = tmp_path / "manifest.json"
    p.write_text('{"id": "x", "name": "X", "version": "1"}')
    assert ModuleManifest.load(p).sensitive_tools == ()
