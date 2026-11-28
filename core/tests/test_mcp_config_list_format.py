"""MCP-Config im alten Listenformat (Task a6e6402c).

Der Installer 87-mcp-servers.sh schrieb mcp_servers.json als nackte JSON-Liste ohne „transport“.
_load_all() erwartete {"servers": [...]} → list_all leer, create/delete mit TypeError → HTTP 500.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from hydrahive.mcp import config as mcp_config
from hydrahive.settings import settings

ALT = [
    {"id": "git", "name": "Git", "command": "npx", "args": ["@modelcontextprotocol/server-git"], "enabled": True},
    {"id": "time", "name": "Time", "command": "npx", "args": ["@modelcontextprotocol/server-time"], "enabled": True},
]


@pytest.fixture
def cfg(tmp_path, monkeypatch) -> Path:
    p = tmp_path / "mcp_servers.json"
    monkeypatch.setattr(settings, "mcp_config", p, raising=False)
    return p


def test_altes_listenformat_wird_gelesen(cfg):
    cfg.write_text(json.dumps(ALT))
    servers = mcp_config.list_all()
    assert [s["id"] for s in servers] == ["git", "time"]
    assert all(s["transport"] == "stdio" for s in servers)


def test_anlegen_und_loeschen_gehen_und_speichern_richtiges_format(cfg):
    cfg.write_text(json.dumps(ALT))
    mcp_config.create(server_id="neu", name="Neu", transport="stdio", command="true", enabled=False)
    assert mcp_config.delete("time") is True
    data = json.loads(cfg.read_text())
    assert isinstance(data, dict)
    assert [s["id"] for s in data["servers"]] == ["git", "neu"]


def test_installer_schreibt_servers_objekt_mit_transport():
    sh = Path(__file__).resolve().parents[2] / "installer" / "modules" / "87-mcp-servers.sh"
    block = re.search(r"<<MCPJSON\n(.*?)\nMCPJSON", sh.read_text(), re.S).group(1)
    data = json.loads(block.replace("$DATA_HOME", "/var/lib/hydrahive2"))
    assert isinstance(data, dict) and len(data["servers"]) == 6
    assert all(s["transport"] == "stdio" for s in data["servers"])
