"""Plugin-System für HydraHive2.

Public API:
    load_all()                — Backend-Start: alle Plugins laden
    REGISTRY                  — geladene Plugins (dict[name, LoadedPlugin])
    tool_bridge               — Plugin-Tool-Namespace + Routing
"""
from hydrahive.plugins.loader import load_all
from hydrahive.plugins.registry import REGISTRY, LoadedPlugin
from hydrahive.plugins import tool_bridge

__all__ = ["load_all", "REGISTRY", "LoadedPlugin", "tool_bridge"]
