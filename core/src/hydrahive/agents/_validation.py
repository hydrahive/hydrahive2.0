from __future__ import annotations

from hydrahive.llm import client as llm_client
from hydrahive.tools import REGISTRY as TOOL_REGISTRY


class AgentValidationError(ValueError):
    pass


_VALID_TYPES = {"master", "project", "specialist"}
_VALID_STATUS = {"active", "disabled"}


def validate_type(agent_type: str) -> None:
    if agent_type not in _VALID_TYPES:
        raise AgentValidationError(
            f"Ungültiger Agent-Typ: '{agent_type}' (erlaubt: {', '.join(_VALID_TYPES)})"
        )


def validate_status(status: str) -> None:
    if status not in _VALID_STATUS:
        raise AgentValidationError(
            f"Ungültiger Status: '{status}' (erlaubt: {', '.join(_VALID_STATUS)})"
        )


def validate_tools(tools: list[str]) -> None:
    if not isinstance(tools, list):
        raise AgentValidationError("tools muss eine Liste sein")
    unknown = [t for t in tools if t not in TOOL_REGISTRY]
    if unknown:
        raise AgentValidationError(
            f"Unbekannte Tools: {', '.join(unknown)}. "
            f"Verfügbar: {', '.join(sorted(TOOL_REGISTRY.keys()))}"
        )


def validate_model(model: str) -> None:
    """Check the model exists in the configured LLM providers — non-fatal if no LLM
    config yet (during first-run setup)."""
    if not model:
        raise AgentValidationError("Modell darf nicht leer sein")
    cfg = llm_client._load_config()
    available: list[str] = []
    for p in cfg.get("providers", []):
        available.extend(p.get("models", []))
    if available and model not in available:
        raise AgentValidationError(
            f"Modell '{model}' ist nicht in der LLM-Konfiguration. "
            f"Verfügbar: {', '.join(available) or '(noch keine)'}"
        )


def validate_temperature(temp: float) -> None:
    if not isinstance(temp, (int, float)):
        raise AgentValidationError("temperature muss eine Zahl sein")
    if temp < 0 or temp > 2:
        raise AgentValidationError("temperature muss zwischen 0 und 2 liegen")


def validate_max_tokens(max_tokens: int) -> None:
    if not isinstance(max_tokens, int) or max_tokens < 1:
        raise AgentValidationError("max_tokens muss eine positive Ganzzahl sein")
    if max_tokens > 200_000:
        raise AgentValidationError("max_tokens > 200000 ist zu viel")
