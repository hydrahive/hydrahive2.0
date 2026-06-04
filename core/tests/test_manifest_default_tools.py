from __future__ import annotations

import json

from hydrahive.modules.manifest import ModuleManifest


def _write(tmp_path, extra):
    d = {"id": "m", "name": "M", "version": "1.0.0", **extra}
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(d))
    return p


def test_flag_true(tmp_path):
    m = ModuleManifest.load(_write(tmp_path, {"default_agent_tools": True}))
    assert m.default_agent_tools is True


def test_flag_defaults_false(tmp_path):
    m = ModuleManifest.load(_write(tmp_path, {}))
    assert m.default_agent_tools is False
