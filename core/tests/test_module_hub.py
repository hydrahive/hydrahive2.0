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


def test_hub_error_on_bad_json(mod_env):
    from hydrahive.settings import settings
    cache = settings.module_hub_cache
    cache.mkdir(parents=True)
    (cache / "hub.json").write_text("not-valid-json{{{")
    with patch("hydrahive.modules.hub_client.refresh"):
        from hydrahive.modules import hub_client
        with pytest.raises(hub_client.HubError, match="hub.json nicht lesbar"):
            hub_client.read_hub_index()
