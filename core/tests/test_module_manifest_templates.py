"""Module bringen eigene Agenten-Templates im Manifest mit (Plan E5)."""
from __future__ import annotations

import json

import pytest

from hydrahive.agents import templates as tpl
from hydrahive.agents.templates import _store
from hydrahive.modules._manifest_templates import ensure_module_templates
from hydrahive.modules.manifest import ManifestError, ModuleManifest

KNOWN = {"claude-sonnet-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"}


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(_store, "_path", lambda: tmp_path / "agent_templates.json")
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: KNOWN)
    monkeypatch.setattr(tpl._defaults, "_current_system_models", lambda: {})
    _store.reset_cache()
    yield
    _store.reset_cache()


def _manifest(tmp_path, extra):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"id": "story", "name": "Story", "version": "1.0.0", **extra}))
    return ModuleManifest.load(p)


def test_manifest_liest_templates(tmp_path):
    m = _manifest(tmp_path, {"templates": [{"id": "story-ghost", "label": "Ghostwriter", "base": "modul-schreiber"}]})
    assert m.templates == (("story-ghost", "Ghostwriter", "modul-schreiber"),)


def test_manifest_ohne_templates(tmp_path):
    assert _manifest(tmp_path, {}).templates == ()


def test_manifest_kaputte_templates(tmp_path):
    with pytest.raises(ManifestError):
        _manifest(tmp_path, {"templates": [{"id": "Böse ID"}]})


def test_fehlendes_template_wird_kopie_der_basis():
    assert ensure_module_templates("story", (("story-ghost", "Ghostwriter", "modul-schreiber"),)) == ["story-ghost"]
    t = tpl.get("story-ghost")
    base = tpl.get("modul-schreiber")
    assert t["label"] == "Ghostwriter" and t["group"] == "modules"
    assert t["chain"] == base["chain"] and t["budget"] == base["budget"]


def test_vorhandenes_template_bleibt_unangetastet():
    ensure_module_templates("story", (("story-ghost", "Ghostwriter", "modul-schreiber"),))
    t = tpl.get("story-ghost")
    tpl.save("story-ghost", {**t, "label": "Admin-Name"}, by="admin")
    assert ensure_module_templates("story", (("story-ghost", "Ghostwriter", "modul-schreiber"),)) == []
    assert tpl.get("story-ghost")["label"] == "Admin-Name"


def test_unbekannte_basis_nimmt_modul_schnell():
    ensure_module_templates("story", (("story-x", "X", "gibt-es-nicht"),))
    assert tpl.get("story-x")["chain"] == tpl.get("modul-schnell")["chain"]
