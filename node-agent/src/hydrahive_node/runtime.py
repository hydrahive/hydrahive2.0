"""Persistent agent runtime; heartbeat transport is implemented in P2.4."""

from __future__ import annotations

from hydrahive_node.storage import AgentIdentity, StatePaths


def run_forever(paths: StatePaths, identity: AgentIdentity) -> None:
    raise RuntimeError("node heartbeat channel is not configured yet")
