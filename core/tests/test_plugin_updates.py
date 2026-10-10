"""Plugins: neue Version erkennen wie bei den Modulen (docs/specs/plugin-updates.md, Task 6c8ac3c7).

Anlass 10.10.2026: file-search 0.2.0 lag im Hub, installiert war 0.1.1 – die Plugin-Verwaltung zeigte das nicht an.
Echte Dateien: Hub-Cache mit hub.json, Plugin-Ordner mit plugin.yaml; REGISTRY wie nach dem Laden.
"""
from __future__ import annotations

import json

import pytest

from hydrahive.plugins.manifest import PluginManifest
from hydrahive.plugins.registry import REGISTRY, LoadedPlugin


@pytest.fixture
def plugin_env(tmp_path, monkeypatch):
    """Hub-Cache + Plugin-Ordner im tmp_path; REGISTRY wird nach dem Test wiederhergestellt."""
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "plugins_dir", tmp_path / "plugins", raising=False)
    monkeypatch.setattr(settings, "plugin_hub_cache", tmp_path / "hub", raising=False)
    (tmp_path / "plugins").mkdir()
    (tmp_path / "hub").mkdir()
    saved = dict(REGISTRY)
    REGISTRY.clear()
    yield tmp_path
    REGISTRY.clear()
    REGISTRY.update(saved)


def _hub(env, **versions):
    (env / "hub" / "hub.json").write_text(json.dumps({"schema_version": 1, "plugins": [
        {"name": n.replace("_", "-"), "version": v, "description": "d", "path": f"plugins/{n}"}
        for n, v in versions.items()]}))


def _installed(env, name, *, loaded, on_disk=None):
    """Plugin wie nach dem Laden: Version ``loaded`` im Speicher, ``on_disk`` (Standard = loaded) in plugin.yaml."""
    d = env / "plugins" / name
    d.mkdir()
    (d / "plugin.yaml").write_text(f"name: {name}\nversion: {on_disk or loaded}\ndescription: d\n")
    REGISTRY[name] = LoadedPlugin(name=name, manifest=PluginManifest(name=name, version=loaded, description="d"),
                                  module=object())


def _by_name(client, headers):
    r = client.get("/api/plugins/installed", headers=headers)
    assert r.status_code == 200, r.text
    return {p["name"]: p for p in r.json()}


def test_newer_version_in_hub_is_reported(client, admin_headers, plugin_env):
    _hub(plugin_env, file_search="0.2.0")
    _installed(plugin_env, "file-search", loaded="0.1.1")
    p = _by_name(client, admin_headers)["file-search"]
    assert (p["version"], p["installed_version"], p["available_version"]) == ("0.1.1", "0.1.1", "0.2.0")
    assert p["update_available"] is True and p["restart_needed"] is False


def test_same_version_no_update(client, admin_headers, plugin_env):
    _hub(plugin_env, file_search="0.2.0")
    _installed(plugin_env, "file-search", loaded="0.2.0")
    p = _by_name(client, admin_headers)["file-search"]
    assert p["update_available"] is False and p["restart_needed"] is False


def test_older_version_in_hub_is_no_update(client, admin_headers, plugin_env):
    _hub(plugin_env, file_search="0.1.0")
    _installed(plugin_env, "file-search", loaded="0.2.0")
    assert _by_name(client, admin_headers)["file-search"]["update_available"] is False


def test_versions_compare_numerically_not_as_text(client, admin_headers, plugin_env):
    _hub(plugin_env, file_search="0.10.0")
    _installed(plugin_env, "file-search", loaded="0.9.0")
    assert _by_name(client, admin_headers)["file-search"]["update_available"] is True


def test_after_update_without_restart_shows_restart_needed_not_update(client, admin_headers, plugin_env):
    """Aktualisieren kopiert 0.2.0 auf die Platte, geladen bleibt 0.1.1 bis zum Neustart."""
    _hub(plugin_env, file_search="0.2.0")
    _installed(plugin_env, "file-search", loaded="0.1.1", on_disk="0.2.0")
    p = _by_name(client, admin_headers)["file-search"]
    assert p["installed_version"] == "0.2.0" and p["version"] == "0.1.1"
    assert p["restart_needed"] is True and p["update_available"] is False


def test_plugin_not_in_hub(client, admin_headers, plugin_env):
    _hub(plugin_env, other="1.0.0")
    _installed(plugin_env, "file-search", loaded="0.1.1")
    p = _by_name(client, admin_headers)["file-search"]
    assert p["available_version"] is None and p["update_available"] is False


def test_without_hub_cache_list_still_works(client, admin_headers, plugin_env, monkeypatch):
    """Kein hub.json: kein Update, kein Fehler – und KEIN git-Aufruf beim Auflisten."""
    from hydrahive.plugins import hub_client

    def no_git(*a, **k):
        raise AssertionError("Liste der installierten Plugins darf den Hub nicht auffrischen")
    monkeypatch.setattr(hub_client, "refresh", no_git)
    _installed(plugin_env, "file-search", loaded="0.1.1")
    p = _by_name(client, admin_headers)["file-search"]
    assert p["available_version"] is None and p["update_available"] is False


def test_broken_hub_json_list_still_works(client, admin_headers, plugin_env):
    (plugin_env / "hub" / "hub.json").write_text("{kaputt")
    _installed(plugin_env, "file-search", loaded="0.1.1")
    assert _by_name(client, admin_headers)["file-search"]["update_available"] is False


def test_update_count(client, admin_headers, plugin_env):
    _hub(plugin_env, file_search="0.2.0", git_stats="0.1.1", code_metrics="0.3.0")
    _installed(plugin_env, "file-search", loaded="0.1.1")
    _installed(plugin_env, "git-stats", loaded="0.1.1")
    _installed(plugin_env, "code-metrics", loaded="0.1.1", on_disk="0.3.0")     # schon aktualisiert, Neustart fehlt
    r = client.get("/api/plugins/update-count", headers=admin_headers)
    assert r.status_code == 200 and r.json() == {"count": 1}


def test_update_count_without_cache_is_zero(client, admin_headers, plugin_env):
    _installed(plugin_env, "file-search", loaded="0.1.1")
    assert client.get("/api/plugins/update-count", headers=admin_headers).json() == {"count": 0}


def test_update_count_requires_admin(client, auth_headers):
    assert client.get("/api/plugins/update-count", headers=auth_headers).status_code == 403
