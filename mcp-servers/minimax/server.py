#!/usr/bin/env python3
"""Launcher: setzt MINIMAX_API_KEY aus llm.json und startet minimax-mcp.

Umgebungsvariablen (optional, überschreiben llm.json):
  MINIMAX_API_KEY          — API-Key
  MINIMAX_MCP_BASE_PATH    — Output-Verzeichnis für Dateien (Default: /tmp/minimax-mcp)
  MINIMAX_API_HOST         — https://api.minimax.io (Global, Default)
  MINIMAX_API_RESOURCE_MODE — url (Default) oder local
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _key_from_llm_json() -> str:
    data_dir = os.environ.get("HH_DATA_DIR", "/var/lib/hydrahive2")
    p = Path(data_dir) / "config" / "llm.json"
    try:
        cfg = json.loads(p.read_text())
        for provider in cfg.get("providers", []):
            if provider.get("id") == "minimax":
                return provider.get("api_key", "")
    except Exception:
        pass
    return ""


if not os.environ.get("MINIMAX_API_KEY"):
    key = _key_from_llm_json()
    if key:
        os.environ["MINIMAX_API_KEY"] = key

if not os.environ.get("MINIMAX_API_KEY"):
    print("FEHLER: MINIMAX_API_KEY nicht gefunden.", file=sys.stderr)
    print("Setze Provider 'minimax' in der LLM-Config oder MINIMAX_API_KEY als ENV-Variable.", file=sys.stderr)
    sys.exit(1)

if not os.environ.get("MINIMAX_MCP_BASE_PATH"):
    os.environ["MINIMAX_MCP_BASE_PATH"] = "/tmp/minimax-mcp"

# minimax-mcp via installed entry-point starten
import subprocess  # noqa: E402
result = subprocess.run(["minimax-mcp"] + sys.argv[1:], env=os.environ)
sys.exit(result.returncode)
