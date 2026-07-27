"""SSOT für die Frage: kann dieses Modell Function-Calling?

Wird vom Runner genutzt, um Modellen ohne Tool-Support gar nicht erst
`tool_schemas` zu schicken. Ohne dieses Gate erfinden solche Modelle Tool-Calls
als Text-JSON, das HydraHive (korrekt) nicht ausführt — das JSON landet dann
stumpf im Chat.

Spec: docs/specs/tool-gate-non-tool-models.md
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _from_registry(model: str) -> bool | None:
    """Tool-Fähigkeit aus dem gewärmten Registry-Cache — ohne Netzwerk-Call.

    Die Registry ist die einzige Ebene, auf der lokale (Ollama, via /api/show)
    und Cloud-Modelle zusammenlaufen. Ollama-Modelle stehen weder in METADATA
    noch im catalog._cache, weil catalog_for_providers sie in einem Sonderzweig
    an _cached_fetch vorbei holt.
    """
    from hydrahive.llm import registry
    cache = registry._cache
    if not cache:
        return None
    for entry in cache[1]:
        if entry.id == model:
            return entry.tool_use
    return None


def _from_metadata(model: str) -> bool | None:
    """Statische Katalog-Metadata: exakter Key, dann ohne Provider-Prefix."""
    from hydrahive.llm._catalog_data import METADATA
    meta = METADATA.get(model) or METADATA.get(model.split("/")[-1])
    return meta.get("tool_use") if meta else None


def model_supports_tools(model: str) -> bool:
    """True, wenn `model` Function-Calling beherrscht.

    Reihenfolge: Registry (live) → statische METADATA → True.

    Der Default ist bewusst fail-open: ein Modell fälschlich ohne Tools zu
    lassen würde einen funktionierenden Agenten stillschweigend entmachten.
    Der umgekehrte Fehler ist sichtbar und harmloser.
    """
    if not model:
        return True
    for source in (_from_registry, _from_metadata):
        value = source(model)
        if value is not None:
            return bool(value)
    return True
