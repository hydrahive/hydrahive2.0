"""Tests für hydrahive.themes.hub_client."""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def theme_hub_env(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data", raising=False)
    monkeypatch.setattr(settings, "theme_hub_cache", tmp_path / "hub", raising=False)
    monkeypatch.setitem(settings.__dict__, "theme_hub_extra_git_urls", [])
    (tmp_path / "data").mkdir()
    return tmp_path


def test_read_hub_index(theme_hub_env):
    from hydrahive.settings import settings
    cache = settings.theme_hub_cache
    cache.mkdir(parents=True)
    (cache / "hub.json").write_text('{"themes":[{"id":"aurora","path":"aurora"}]}')
    with patch("hydrahive.themes.hub_client.refresh"):
        from hydrahive.themes.hub_client import read_hub_index
        idx = read_hub_index()
    assert idx["themes"][0]["id"] == "aurora"


def test_read_hub_index_triggers_refresh_when_missing(theme_hub_env):
    from hydrahive.settings import settings
    cache = settings.theme_hub_cache
    cache.mkdir(parents=True)

    def fake_refresh():
        (cache / "hub.json").write_text('{"themes":[]}')

    with patch("hydrahive.themes.hub_client.refresh", side_effect=fake_refresh):
        from hydrahive.themes import hub_client
        idx = hub_client.read_hub_index()
    assert idx == {"themes": []}


def test_theme_source_path_valid(theme_hub_env):
    from hydrahive.settings import settings
    cache = settings.theme_hub_cache
    cache.mkdir(parents=True)
    (cache / "aurora").mkdir()
    from hydrahive.themes.hub_client import theme_source_path
    assert theme_source_path("aurora") == (cache / "aurora").resolve()


def test_theme_source_path_blocks_traversal(theme_hub_env):
    from hydrahive.settings import settings
    settings.theme_hub_cache.mkdir(parents=True, exist_ok=True)
    from hydrahive.themes.hub_client import theme_source_path, HubError
    with pytest.raises(HubError, match="ungültiger theme-path"):
        theme_source_path("../../etc/passwd")


def test_theme_source_path_blocks_sibling_prefix(theme_hub_env):
    from hydrahive.settings import settings
    settings.theme_hub_cache.mkdir(parents=True, exist_ok=True)
    from hydrahive.themes.hub_client import theme_source_path, HubError
    with pytest.raises(HubError):
        theme_source_path(f"../{settings.theme_hub_cache.name}-evil/x")


def test_hub_error_on_bad_json(theme_hub_env):
    from hydrahive.settings import settings
    cache = settings.theme_hub_cache
    cache.mkdir(parents=True)
    (cache / "hub.json").write_text("not-valid-json{{{")
    with patch("hydrahive.themes.hub_client.refresh"):
        from hydrahive.themes import hub_client
        with pytest.raises(hub_client.HubError, match="hub.json nicht lesbar"):
            hub_client.read_hub_index()


# --- Multi-Hub --------------------------------------------------------------

def test_theme_hub_extra_git_urls_parsed(monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setenv("HH_THEME_HUB_GIT_URLS", "http://g/a.git, http://g/a.git ,http://g/b.git")
    settings.__dict__.pop("theme_hub_extra_git_urls", None)
    try:
        assert settings.theme_hub_extra_git_urls == ["http://g/a.git", "http://g/b.git"]
    finally:
        settings.__dict__.pop("theme_hub_extra_git_urls", None)


def _seed_two_hubs(s, monkeypatch, primary_json: str, extra_json: str):
    from hydrahive.themes import hub_client
    primary = s.theme_hub_cache
    primary.mkdir(parents=True, exist_ok=True)
    (primary / "hub.json").write_text(primary_json)
    extra_url = "http://gitea.local/hydrahive/themes-internal.git"
    slug = hub_client._slug(extra_url)
    extra = primary.parent / f"hub-{slug}"
    extra.mkdir(parents=True, exist_ok=True)
    (extra / "hub.json").write_text(extra_json)
    monkeypatch.setitem(s.__dict__, "theme_hub_extra_git_urls", [extra_url])
    return slug, extra


def test_read_hub_index_merges_two_hubs(theme_hub_env, monkeypatch):
    from hydrahive.settings import settings
    from hydrahive.themes import hub_client
    slug, _ = _seed_two_hubs(
        settings, monkeypatch,
        '{"themes":[{"id":"aurora","path":"aurora"}]}',
        '{"themes":[{"id":"midnight","path":"midnight"}]}',
    )
    by = {t["id"]: t for t in hub_client.read_hub_index()["themes"]}
    assert set(by) == {"aurora", "midnight"}
    assert by["aurora"]["_hub"] is None
    assert by["midnight"]["_hub"] == slug


def test_read_hub_index_dedupes_primary_wins(theme_hub_env, monkeypatch):
    from hydrahive.settings import settings
    from hydrahive.themes import hub_client
    _seed_two_hubs(
        settings, monkeypatch,
        '{"themes":[{"id":"dup","path":"primary-path"}]}',
        '{"themes":[{"id":"dup","path":"gitea-path"}]}',
    )
    dup = [t for t in hub_client.read_hub_index()["themes"] if t["id"] == "dup"]
    assert len(dup) == 1
    assert dup[0]["path"] == "primary-path" and dup[0]["_hub"] is None
