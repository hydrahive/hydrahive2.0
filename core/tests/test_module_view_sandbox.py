"""Modul-Ansichten im Chat, abgeschottet (Spec docs/specs/module-view-sandbox.md).

Gemessen 20.10.2026: App-CSP + eigene CSP auf einer Antwort → Inline-Skripte blockiert. Darum eine feste
nginx-Ausnahme für /api/module-device/<id>/sandbox/ und eine neue Werkzeug-Ergebnis-Art `module_view`.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from hydrahive.modules import registry
from hydrahive.runner.dispatcher import to_tool_result_block
from hydrahive.tools.base import ToolResult

ROOT = Path(__file__).resolve().parents[2]
SANDBOX_CSP = ("sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox; default-src 'none'; "
               "script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; "
               "connect-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'self'")


# --- nginx -----------------------------------------------------------------------------------------

def _conf() -> str:
    return (ROOT / "installer/modules/60-nginx.sh").read_text()


def _sandbox_block() -> str:
    conf = _conf()
    start = conf.index("location ~ ^/api/module-device/[a-z0-9-]+/sandbox/ {")
    return conf[start:conf.index("\n    }\n", start)]


def test_nginx_has_exactly_one_sandbox_location():
    assert _conf().count("/sandbox/ {") == 1
    assert "hh_module_sandbox" in _sandbox_block()


def test_sandbox_location_sets_fixed_sandbox_csp_and_not_the_app_csp():
    block = _sandbox_block()
    assert f'add_header Content-Security-Policy "{SANDBOX_CSP}" always;' in block
    assert "script-src 'self'" not in block and "unsafe-eval" not in block
    for header in ('X-Content-Type-Options "nosniff"', 'Referrer-Policy "no-referrer"',
                   'X-Frame-Options "SAMEORIGIN"', 'Cache-Control "no-store"', "Strict-Transport-Security"):
        assert f"add_header {header}" in block, header


def test_sandbox_location_proxies_to_core_and_limits_body():
    block = _sandbox_block()
    assert re.search(r"proxy_pass http://\$HH_HOST:\$HH_PORT;", block)
    assert "proxy_set_header X-Forwarded-For" in block
    assert "client_max_body_size 64k;" in block


def test_api_prefix_location_does_not_shadow_the_regex():
    """Ein `^~` vor /api/ würde die Regex-Ausnahme stillschweigend aushebeln."""
    assert "location ^~ /api/ " not in _conf()
    assert "location /api/ {" in _conf()


def test_updater_rewrites_nginx_without_the_sandbox_marker():
    assert 'grep -q "hh_module_sandbox"' in (ROOT / "installer/update.sh").read_text()


# --- Dispatcher: module_view -----------------------------------------------------------------------

@pytest.fixture
def loaded(monkeypatch):
    fake = registry.LoadedModule(name="diagramme", manifest=None, path=Path("/x"), loaded=True)
    off = registry.LoadedModule(name="aus", manifest=None, path=Path("/y"), loaded=False)
    monkeypatch.setattr(registry, "REGISTRY", {"diagramme": fake, "aus": off})


def _view(**meta) -> ToolResult:
    base = {"module": "diagramme", "view_id": "d_01ABC-xyz", "title": "Websuche"}
    base.update(meta)
    return ToolResult.ok("Diagramm erstellt", result_type="module_view", **base)


def test_module_view_becomes_media_entry(loaded):
    block = to_tool_result_block("t1", _view())
    assert block["media"] == [{"kind": "module_view", "module": "diagramme", "view_id": "d_01ABC-xyz",
                               "title": "Websuche"}]
    assert block["content"] == "Diagramm erstellt"


def test_title_is_cut_to_200_and_missing_title_is_empty(loaded):
    assert to_tool_result_block("t1", _view(title="x" * 500))["media"][0]["title"] == "x" * 200
    r = ToolResult.ok("ok", result_type="module_view", module="diagramme", view_id="abc")
    assert to_tool_result_block("t1", r)["media"][0]["title"] == ""


@pytest.mark.parametrize("meta", [
    {"module": "unbekannt"}, {"module": "aus"}, {"module": "Diagramme"}, {"module": "../x"}, {"module": None},
    {"view_id": ""}, {"view_id": "a/b"}, {"view_id": "x" * 65}, {"view_id": "a b"}, {"view_id": 7},
])
def test_invalid_module_view_gives_no_media(loaded, meta):
    assert "media" not in to_tool_result_block("t1", _view(**meta))


def test_module_name_is_checked_even_if_registry_has_odd_key(monkeypatch):
    """Doppelte Absicherung: auch ein seltsamer Schlüssel in der Modul-Liste wird nicht durchgereicht."""
    odd = registry.LoadedModule(name="x", manifest=None, path=Path("/z"), loaded=True)
    monkeypatch.setattr(registry, "REGISTRY", {"../x": odd, "Gross": odd})
    for module in ("../x", "Gross"):
        assert "media" not in to_tool_result_block("t1", _view(module=module))


def test_failed_result_never_gives_module_view(loaded):
    r = ToolResult(success=False, error="kaputt", result_type="module_view",
                   metadata={"module": "diagramme", "view_id": "abc", "title": "t"})
    assert "media" not in to_tool_result_block("t1", r)


def test_title_must_be_text(loaded):
    assert to_tool_result_block("t1", _view(title=["a"]))["media"][0]["title"] == ""
