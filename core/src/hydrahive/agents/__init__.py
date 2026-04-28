"""Agent-Layer: persistence, validation, system-prompt, bootstrap.

Public API:
    config           — CRUD + system-prompt accessors
    bootstrap        — first-run helpers (ensure_master)
    AgentValidationError — raised for invalid configs
    workspace_for    — resolves the workspace path for a given agent
"""

from hydrahive.agents import bootstrap, config
from hydrahive.agents._paths import workspace_for
from hydrahive.agents._validation import AgentValidationError

__all__ = [
    "config",
    "bootstrap",
    "workspace_for",
    "AgentValidationError",
]
