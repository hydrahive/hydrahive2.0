"""Tests für hydrahive.modules.hub_client."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


def test_read_hub_index(mod_env):
    from hydrahive.settings import settings
    cache = settings.module_hub_cache
    cache.mkdir(parents=True)
    (cache / "hub.json").write_text('{"modules":[{"id":"example","path":"example"}]}')
    with patch("hydrahive.modules.hub_client.refresh"):  # kein echtes git
        from hydrahive.modules.hub_client import read_hub_index
        idx = read_hub_index()
    assert idx["modules"][0]["id"] == "example"


def test_read_hub_index_triggers_refresh_when_missing(mod_env):
    """Wenn hub.json fehlt, wird refresh() aufgerufen."""
    from hydrahive.settings import settings
    cache = settings.module_hub_cache
    cache.mkdir(parents=True)

    def fake_refresh():
        (cache / "hub.json").write_text('{"modules":[]}')

    with patch("hydrahive.modules.hub_client.refresh", side_effect=fake_refresh):
        from hydrahive.modules import hub_client
        idx = hub_client.read_hub_index()
    assert idx == {"modules": []}


def test_module_source_path_valid(mod_env):
    from hydrahive.settings import settings
    cache = settings.module_hub_cache
    cache.mkdir(parents=True)
    (cache / "example").mkdir()
    from hydrahive.modules.hub_client import module_source_path
    result = module_source_path("example")
    assert result == (cache / "example").resolve()


def test_module_source_path_escape_blocked(mod_env):
    """Path-Escape ausm Cache wird blockiert."""
    from hydrahive.settings import settings
    cache = settings.module_hub_cache
    cache.mkdir(parents=True)
    from hydrahive.modules.hub_client import HubError, module_source_path
    with pytest.raises(HubError, match="ungültiger module-path"):
        module_source_path("../../etc/passwd")


def test_module_source_path_blocks_sibling_prefix(mod_env):
    import pytest
    from hydrahive.modules.hub_client import module_source_path, HubError
    from hydrahive.settings import settings
    settings.module_hub_cache.mkdir(parents=True, exist_ok=True)
    # ../<cachename>-evil teilt den String-Prefix, ist aber außerhalb der Grenze
    with pytest.raises(HubError):
        module_source_path(f"../{settings.module_hub_cache.name}-evil/x")


def test_module_source_path_blocks_traversal(mod_env):
    import pytest
    from hydrahive.modules.hub_client import module_source_path, HubError
    from hydrahive.settings import settings
    settings.module_hub_cache.mkdir(parents=True, exist_ok=True)
    with pytest.raises(HubError):
        module_source_path("../../etc/passwd")


def test_module_source_path_allows_valid(mod_env):
    from hydrahive.modules.hub_client import module_source_path
    from hydrahive.settings import settings
    settings.module_hub_cache.mkdir(parents=True, exist_ok=True)
    assert module_source_path("example") == (settings.module_hub_cache.resolve() / "example")


def test_hub_error_on_bad_json(mod_env):
    from hydrahive.settings import settings
    cache = settings.module_hub_cache
    cache.mkdir(parents=True)
    (cache / "hub.json").write_text("not-valid-json{{{")
    with patch("hydrahive.modules.hub_client.refresh"):
        from hydrahive.modules import hub_client
        with pytest.raises(hub_client.HubError, match="hub.json nicht lesbar"):
            hub_client.read_hub_index()


# --- Multi-Hub --------------------------------------------------------------

def test_module_hub_extra_git_urls_parsed(monkeypatch):
    """Komma-Liste, getrimmt, dedupliziert, ohne die primäre URL."""
    from hydrahive.settings import settings

    monkeypatch.setenv("HH_MODULE_HUB_GIT_URLS", "http://g/a.git, http://g/a.git ,http://g/b.git")
    settings.__dict__.pop("module_hub_extra_git_urls", None)
    try:
        assert settings.module_hub_extra_git_urls == ["http://g/a.git", "http://g/b.git"]
    finally:
        settings.__dict__.pop("module_hub_extra_git_urls", None)


def test_module_hub_extra_git_urls_override_wins(monkeypatch, tmp_path):
    """GUI-Override schlägt Env (Override → Env → Default)."""
    from hydrahive.settings import settings

    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    (tmp_path / "overrides.json").write_text('{"module_hub_extra_git_urls":"http://gitea/x.git"}')
    monkeypatch.setenv("HH_MODULE_HUB_GIT_URLS", "http://env/y.git")
    settings.__dict__.pop("module_hub_extra_git_urls", None)
    try:
        assert settings.module_hub_extra_git_urls == ["http://gitea/x.git"]
    finally:
        settings.__dict__.pop("module_hub_extra_git_urls", None)


def _seed_two_hubs(s, monkeypatch, primary_json: str, extra_json: str):
    """Primär- + einen Extra-Hub-Cache mit hub.json anlegen. Liefert (slug, extra_dir)."""
    from hydrahive.modules import hub_client

    primary = s.module_hub_cache
    primary.mkdir(parents=True, exist_ok=True)
    (primary / "hub.json").write_text(primary_json)
    extra_url = "http://gitea.local/hydrahive/internal.git"
    slug = hub_client._slug(extra_url)
    extra = primary.parent / f"hub-{slug}"
    extra.mkdir(parents=True, exist_ok=True)
    (extra / "hub.json").write_text(extra_json)
    monkeypatch.setitem(s.__dict__, "module_hub_extra_git_urls", [extra_url])
    return slug, extra


def test_read_hub_index_merges_two_hubs(mod_env, monkeypatch):
    from hydrahive.settings import settings
    from hydrahive.modules import hub_client

    slug, _ = _seed_two_hubs(
        settings, monkeypatch,
        '{"modules":[{"id":"example","path":"example"}]}',
        '{"modules":[{"id":"rom","path":"rom"}]}',
    )
    by = {m["id"]: m for m in hub_client.read_hub_index()["modules"]}
    assert set(by) == {"example", "rom"}
    assert by["example"]["_hub"] is None     # primär
    assert by["rom"]["_hub"] == slug         # interner Hub


def test_read_hub_index_dedupes_primary_wins(mod_env, monkeypatch):
    from hydrahive.settings import settings
    from hydrahive.modules import hub_client

    _seed_two_hubs(
        settings, monkeypatch,
        '{"modules":[{"id":"dup","path":"primary-path"}]}',
        '{"modules":[{"id":"dup","path":"gitea-path"}]}',
    )
    dup = [m for m in hub_client.read_hub_index()["modules"] if m["id"] == "dup"]
    assert len(dup) == 1
    assert dup[0]["path"] == "primary-path" and dup[0]["_hub"] is None


def test_module_source_path_resolves_per_hub(mod_env, monkeypatch):
    from hydrahive.settings import settings
    from hydrahive.modules import hub_client

    slug, extra = _seed_two_hubs(settings, monkeypatch, '{"modules":[]}', '{"modules":[]}')
    (extra / "rom").mkdir()
    (settings.module_hub_cache / "example").mkdir()

    assert hub_client.module_source_path("rom", slug) == (extra / "rom").resolve()
    assert hub_client.module_source_path("example", None) == (
        settings.module_hub_cache / "example"
    ).resolve()


def test_installer_cache_path_for_uses_hub(mod_env, monkeypatch):
    from hydrahive.settings import settings
    from hydrahive.modules import hub_client, installer

    slug, extra = _seed_two_hubs(
        settings, monkeypatch,
        '{"modules":[]}',
        '{"modules":[{"id":"rom","path":"rom"}]}',
    )
    (extra / "rom").mkdir()
    assert installer._cache_path_for("rom") == (extra / "rom").resolve()


# --- Selbstheilung bei divergierter Hub-History --------------------------

def _fake_proc(returncode=0, stdout="", stderr=""):
    """Minimaler CompletedProcess-Ersatz für gemockte _run_git-Aufrufe."""
    from types import SimpleNamespace
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_refresh_one_ff_pull_erfolg_kein_reset(mod_env, tmp_path):
    """Normaler Fall: pull --ff-only klappt → kein fetch/reset-Fallback."""
    from hydrahive.modules import hub_client

    cache = tmp_path / "hub"
    (cache / ".git").mkdir(parents=True)
    calls = []

    def fake_git(args, cwd=None):
        calls.append(args)
        return _fake_proc(returncode=0)

    with patch.object(hub_client, "_run_git", side_effect=fake_git):
        hub_client._refresh_one(cache, "http://x/y.git")

    assert calls == [["pull", "--ff-only"]]  # nur pull, kein reset


def test_refresh_one_divergenz_heilt_per_reset(mod_env, tmp_path):
    """ff-only schlägt fehl (divergierte History) → fetch + reset --hard origin/<branch>."""
    from hydrahive.modules import hub_client

    cache = tmp_path / "hub"
    (cache / ".git").mkdir(parents=True)
    calls = []

    def fake_git(args, cwd=None):
        calls.append(args)
        if args[:2] == ["pull", "--ff-only"]:
            return _fake_proc(returncode=1, stderr="Not possible to fast-forward")
        if args[:2] == ["rev-parse", "--abbrev-ref"]:
            return _fake_proc(returncode=0, stdout="main\n")
        return _fake_proc(returncode=0)

    with patch.object(hub_client, "_run_git", side_effect=fake_git):
        hub_client._refresh_one(cache, "http://x/y.git")  # darf NICHT werfen

    assert ["pull", "--ff-only"] in calls
    assert ["fetch", "origin"] in calls
    assert ["reset", "--hard", "origin/main"] in calls


def test_refresh_one_divergenz_nutzt_aktuellen_branch(mod_env, tmp_path):
    """Der hart resyncte Branch folgt dem tatsächlichen HEAD des Caches."""
    from hydrahive.modules import hub_client

    cache = tmp_path / "hub"
    (cache / ".git").mkdir(parents=True)
    calls = []

    def fake_git(args, cwd=None):
        calls.append(args)
        if args[:2] == ["pull", "--ff-only"]:
            return _fake_proc(returncode=1, stderr="diverged")
        if args[:2] == ["rev-parse", "--abbrev-ref"]:
            return _fake_proc(returncode=0, stdout="release\n")
        return _fake_proc(returncode=0)

    with patch.object(hub_client, "_run_git", side_effect=fake_git):
        hub_client._refresh_one(cache, "http://x/y.git")

    assert ["reset", "--hard", "origin/release"] in calls


def test_refresh_one_reset_fehler_wirft(mod_env, tmp_path):
    """Schlägt sogar der Reset fehl, wird ein HubError gemeldet (nicht still)."""
    from hydrahive.modules import hub_client

    cache = tmp_path / "hub"
    (cache / ".git").mkdir(parents=True)

    def fake_git(args, cwd=None):
        if args[:2] == ["pull", "--ff-only"]:
            return _fake_proc(returncode=1, stderr="diverged")
        if args[:2] == ["rev-parse", "--abbrev-ref"]:
            return _fake_proc(returncode=0, stdout="main\n")
        if args[0] == "reset":
            return _fake_proc(returncode=1, stderr="reset boom")
        return _fake_proc(returncode=0)

    with patch.object(hub_client, "_run_git", side_effect=fake_git):
        with pytest.raises(hub_client.HubError, match="git reset failed"):
            hub_client._refresh_one(cache, "http://x/y.git")
