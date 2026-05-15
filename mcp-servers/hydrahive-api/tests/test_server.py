"""Tests für server.py — FastMCP Entry Point mit 20 Tools."""
from __future__ import annotations

import importlib
import sys


def _import_server():
    """Importiert server ohne env vars — darf nicht knallen."""
    if "server" in sys.modules:
        return sys.modules["server"]
    return importlib.import_module("server")


def test_server_importierbar_ohne_env_vars():
    """server.py muss importierbar sein, auch wenn keine Umgebungsvariablen gesetzt sind."""
    mod = _import_server()
    assert mod is not None


def test_mcp_objekt_existiert():
    """Das FastMCP-Singleton muss auf Modulebene verfügbar sein."""
    from mcp.server.fastmcp import FastMCP

    mod = _import_server()
    assert hasattr(mod, "mcp"), "server.mcp fehlt"
    assert isinstance(mod.mcp, FastMCP), f"server.mcp ist kein FastMCP, sondern {type(mod.mcp)}"


def test_mcp_name():
    """Der MCP-Server heißt 'hydrahive'."""
    mod = _import_server()
    assert mod.mcp.name == "hydrahive"


def test_alle_20_tools_registriert():
    """Alle 20 MCP-Tools müssen in mcp._tool_manager._tools stehen."""
    mod = _import_server()
    registered = set(mod.mcp._tool_manager._tools.keys())

    expected = {
        "hh_status",
        "hh_token_stats",
        "hh_list_sessions",
        "hh_get_session",
        "hh_get_messages",
        "hh_send_message",
        "hh_list_agents",
        "hh_get_agent",
        "hh_update_agent",
        "hh_list_projects",
        "hh_list_files",
        "hh_read_file",
        "hh_dm_search",
        "hh_dm_get_session",
        "hh_dm_list_sessions",
        "hh_dm_stats",
        "hh_al_status",
        "hh_al_send",
        "hh_al_check_inbox",
        "hh_al_reply",
    }

    fehlend = expected - registered
    unerwartet = registered - expected

    assert not fehlend, f"Fehlende Tools: {sorted(fehlend)}"
    assert not unerwartet, f"Unerwartete Tools: {sorted(unerwartet)}"


def test_genau_20_tools():
    """Es müssen exakt 20 Tools registriert sein — nicht mehr, nicht weniger."""
    mod = _import_server()
    count = len(mod.mcp._tool_manager._tools)
    assert count == 20, f"Erwartet 20 Tools, gefunden: {count}"


def test_globale_singletons_existieren():
    """_auth, _rest und _al müssen als Modul-Singletons verfügbar sein."""
    from _auth import Auth
    from _rest import RestClient
    from _agentlink import AgentLinkClient

    mod = _import_server()
    assert hasattr(mod, "_auth"), "server._auth fehlt"
    assert hasattr(mod, "_rest"), "server._rest fehlt"
    assert hasattr(mod, "_al"), "server._al fehlt"
    assert isinstance(mod._auth, Auth)
    assert isinstance(mod._rest, RestClient)
    assert isinstance(mod._al, AgentLinkClient)
