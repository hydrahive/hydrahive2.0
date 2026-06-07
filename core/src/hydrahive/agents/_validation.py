from __future__ import annotations

from hydrahive.plugins import tool_bridge as plugin_bridge
from hydrahive.tools import OPTIONAL_TOOLS, REGISTRY as TOOL_REGISTRY


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
    plugin_names = {t["name"] for t in plugin_bridge.all_tool_meta()}
    unknown = [
        t for t in tools
        if t not in TOOL_REGISTRY and t not in plugin_names and t not in OPTIONAL_TOOLS
    ]
    if unknown:
        available = sorted(set(TOOL_REGISTRY.keys()) | plugin_names)
        raise AgentValidationError(
            f"Unbekannte Tools: {', '.join(unknown)}. "
            f"Verfügbar: {', '.join(available)}"
        )


def _available_models() -> list[str]:
    """Verfügbare Modell-IDs: aus der kanonischen Registry (Cache).
    Leere Liste → validate_model winkt durch (Erst-Setup / Fetch-Fehler)."""
    from hydrahive.llm import registry
    return sorted(registry.known_ids())


def validate_model(model: str) -> None:
    """Modell darf nicht leer sein; wenn eine Live-Liste vorliegt, muss das Modell
    drin sein — sonst (leere Liste) durchwinken (Erst-Setup / Fetch-Fehler)."""
    if not model:
        raise AgentValidationError("Modell darf nicht leer sein")
    available = _available_models()
    if available and model not in available:
        raise AgentValidationError(
            f"Modell '{model}' ist nicht in der Live-Modell-Liste verfügbar."
        )


def validate_fallback_models(models: list[str]) -> None:
    if not isinstance(models, list):
        raise AgentValidationError("fallback_models muss eine Liste sein")
    for m in models:
        if not isinstance(m, str) or not m:
            raise AgentValidationError("fallback_models darf keine leeren Einträge enthalten")
        validate_model(m)


_TOOL_CONFIG_BLOCKS = {
    "smtp": {"host", "port", "user", "password", "from", "use_tls"},
    "imap": {"host", "port", "user", "password"},
}


def validate_tool_config(tc: object) -> None:
    """Per-Agent tool_config: aktuell nur smtp/imap-Postfach-Overrides.

    Strikt — unbekannte Schlüssel werden abgelehnt (fail fast), damit kein
    Tippfehler still ins Leere läuft."""
    if not isinstance(tc, dict):
        raise AgentValidationError("tool_config muss ein Objekt sein")
    unknown = set(tc) - set(_TOOL_CONFIG_BLOCKS)
    if unknown:
        raise AgentValidationError(
            f"tool_config: unbekannte Schlüssel {sorted(unknown)} "
            f"(erlaubt: {sorted(_TOOL_CONFIG_BLOCKS)})"
        )
    for block, allowed in _TOOL_CONFIG_BLOCKS.items():
        if block not in tc:
            continue
        b = tc[block]
        if not isinstance(b, dict):
            raise AgentValidationError(f"tool_config.{block} muss ein Objekt sein")
        unk = set(b) - allowed
        if unk:
            raise AgentValidationError(
                f"tool_config.{block}: unbekannte Schlüssel {sorted(unk)}"
            )
        if "port" in b:
            try:
                int(b["port"])
            except (TypeError, ValueError):
                raise AgentValidationError(f"tool_config.{block}.port muss eine Zahl sein")


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


def validate_compact_model(model: str) -> None:
    """Compact-Modell darf leer sein (= nutze main llm_model). Wenn gesetzt
    muss es ein bekanntes Modell sein."""
    if not model:
        return
    validate_model(model)


def validate_compact_tool_result_limit(limit: int) -> None:
    if not isinstance(limit, int) or limit < 100:
        raise AgentValidationError("compact_tool_result_limit muss ≥ 100 sein")
    if limit > 50_000:
        raise AgentValidationError("compact_tool_result_limit > 50000 ist zu viel")


def validate_compact_reserve_tokens(reserve: int) -> None:
    if not isinstance(reserve, int) or reserve < 1000:
        raise AgentValidationError("compact_reserve_tokens muss ≥ 1000 sein")
    if reserve > 100_000:
        raise AgentValidationError("compact_reserve_tokens > 100000 ist zu viel")


def validate_compact_threshold_pct(pct: int) -> None:
    if not isinstance(pct, int) or pct < 30 or pct > 100:
        raise AgentValidationError("compact_threshold_pct muss zwischen 30 und 100 liegen")


def validate_max_iterations(n: int) -> None:
    if not isinstance(n, int) or n < 1:
        raise AgentValidationError("max_iterations muss ≥ 1 sein")
    if n > 250:
        raise AgentValidationError("max_iterations > 250 ist exzessiv — wahrscheinlich Konfig-Fehler")


def normalize_compact_changes(changes: dict) -> None:
    """Normalizes compaction fields in-place: None/empty → remove or default."""
    if "compact_model" in changes:
        if changes["compact_model"] is None:
            changes["compact_model"] = ""
        validate_compact_model(changes["compact_model"])
    for field, validator in (
        ("compact_tool_result_limit", validate_compact_tool_result_limit),
        ("compact_reserve_tokens", validate_compact_reserve_tokens),
        ("compact_threshold_pct", validate_compact_threshold_pct),
        ("max_iterations", validate_max_iterations),
    ):
        if field not in changes:
            continue
        if changes[field] in (None, ""):
            changes.pop(field)
        else:
            changes[field] = int(changes[field])
            validator(changes[field])
