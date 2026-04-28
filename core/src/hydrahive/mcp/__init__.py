"""MCP-Layer: Model Context Protocol Integration.

Phase 1 (jetzt): stdio-Transport. Server-Registry, Connection-Manager,
Tool-Bridge in den Runner.
Phase 2 (später): HTTP / SSE-Transports.
"""

from hydrahive.mcp import config, manager, tool_bridge
from hydrahive.mcp._validation import McpValidationError

__all__ = ["config", "manager", "tool_bridge", "McpValidationError"]
