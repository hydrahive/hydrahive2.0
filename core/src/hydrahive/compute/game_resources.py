"""Public store facade for project-bound Game Studio workspace resources.

Browser-facing callers can only create or rotate resources into ``pending``.
``confirm_workspace`` remains an internal store contract for a future caller
that has already authenticated the node identity; no public API exposes it.
"""

from hydrahive.compute import audit
from hydrahive.compute._game_approvals import (
    approve_isolation,
    get_isolation_approval,
    list_isolation_approvals,
)
from hydrahive.compute._game_execution_binding import validate_execution_binding
from hydrahive.compute._game_resource_common import (
    ExecutionBindingError,
    GameResourceError,
    normalize_engine_project_relpath,
)
from hydrahive.compute._game_resource_revoke import (
    revoke_for_node_in_connection,
    revoke_isolation_approval,
)
from hydrahive.compute._game_workspace_lifecycle import confirm_workspace, revoke_workspace
from hydrahive.compute._game_workspace_rotation import rotate_workspace
from hydrahive.compute._game_workspaces import create_workspace, get_workspace, list_workspaces

__all__ = [
    "ExecutionBindingError",
    "GameResourceError",
    "approve_isolation",
    "audit",
    "confirm_workspace",
    "create_workspace",
    "get_isolation_approval",
    "get_workspace",
    "list_isolation_approvals",
    "list_workspaces",
    "normalize_engine_project_relpath",
    "revoke_for_node_in_connection",
    "revoke_isolation_approval",
    "revoke_workspace",
    "rotate_workspace",
    "validate_execution_binding",
]
