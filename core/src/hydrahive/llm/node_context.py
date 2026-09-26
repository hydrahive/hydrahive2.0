"""Public execution-node context for LLM catalog responses.

The catalog must never infer remote hardware from the HydraHive host.  Providers
may explicitly reference an existing compute node; legacy providers get a stable
provider-scoped identity until they are assigned to a node.
"""
from __future__ import annotations

from typing import Any

from hydrahive.compute import db as node_db


def _legacy_node_id(provider: dict[str, Any]) -> str:
    provider_id = str(provider.get("id") or "provider").strip()
    return f"provider:{provider_id}"


def _explicit_node_id(provider: dict[str, Any]) -> str | None:
    value = provider.get("node_id")
    if value is None:
        return None
    node_id = str(value).strip()
    if not node_id or len(node_id) > 128:
        return None
    return node_id


def for_provider(provider: dict[str, Any] | None) -> dict[str, str]:
    """Return safe, endpoint-free node metadata for a configured provider.

    ``node_id`` is deliberately not derived from an IP address.  Legacy
    providers receive a stable provider-scoped identity, while explicitly
    assigned compute nodes expose only their public registry metadata.
    """
    provider = provider or {}
    node_id = _explicit_node_id(provider) or _legacy_node_id(provider)
    node = node_db.get_node(node_id) if provider.get("node_id") else None
    if node is None:
        return {
            "node_id": node_id,
            "node_name": str(provider.get("node_name") or provider.get("name") or provider.get("id") or node_id),
            "node_kind": "provider",
            "node_status": "configured" if not provider.get("node_id") else "unknown",
            "hardware_source": "unknown",
        }
    return {
        "node_id": node.node_id,
        "node_name": node.name,
        "node_kind": node.kind,
        "node_status": node.status,
        "hardware_source": "compute_node",
    }
