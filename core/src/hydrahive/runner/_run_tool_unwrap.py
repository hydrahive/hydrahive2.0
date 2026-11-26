"""run_tool auspacken (Katalog Etappe 2, Spec E4/S1): VOR jeder Prüfung des Runners.

Aus ``run_tool(name, args)`` wird ein normaler Tool-Aufruf ``{name: inner, input: args, via: "run_tool"}``. Er nimmt danach
denselben Weg wie ein direkter Aufruf: Bestätigung (Harakiri, ALWAYS_CONFIRM, Discord-Admin), ``vault_gate``,
``tool_denied``, Container-Allowlist (über ``allowed_tools``), Eintrag in ``tool_calls`` (innerer Name, ``via`` in den
Metadaten) und die Sperr-Erkennung im Agenten-Baum. Die Tool-Liste an das Modell bleibt dabei unverändert (E4).

Die Freigabe des Laufs ist ``allowed_tools`` (= ``effective_tool_names`` + MCP). Ein Tool, das dort fehlt, wird abgelehnt.
"""
from __future__ import annotations

VIA = "run_tool"
OUTER = "run_tool"
#: Als innerer Name verboten: kein Auspacken im Auspacken, keine Such-Werkzeuge über den Umweg.
from hydrahive.catalog import CATALOG_TOOLS as FORBIDDEN_INNER  # noqa: E402

_TYPES: dict[str, tuple] = {
    "string": (str,), "integer": (int,), "number": (int, float), "boolean": (bool,),
    "array": (list,), "object": (dict,),
}


def _type_ok(value, kind: str) -> bool:
    types = _TYPES.get(kind)
    if types is None:
        return True                                   # unbekannter Typ: nicht raten, durchlassen
    if kind in ("integer", "number") and isinstance(value, bool):
        return False                                  # bool ist in Python ein int – für Tools aber kein Zahlenwert
    return isinstance(value, types)


def check_args(schema: dict | None, args) -> str | None:
    """Schlanke Prüfung der Argumente gegen ein Tool-Schema, ohne neue Abhängigkeit.

    Unterstützt, was die Tool-Schemas nutzen: ``type: object``, ``required``, ``properties.*.type``, ``enum`` und
    unbekannte Felder. Liefert einen deutschen Fehlertext mit den erlaubten Feldern oder ``None``.
    """
    schema = schema or {}
    if not isinstance(args, dict):
        return "Die Argumente müssen ein Objekt sein (args = {…})."
    props: dict = schema.get("properties") or {}
    allowed = ", ".join(sorted(props)) or "(keine)"
    unknown = sorted(k for k in args if k not in props) if props or schema.get("type") == "object" else []
    if unknown:
        return f"Unbekannte Felder: {', '.join(unknown)}. Erlaubt sind: {allowed}."
    missing = [k for k in (schema.get("required") or []) if k not in args]
    if missing:
        return f"Pflichtfelder fehlen: {', '.join(missing)}. Erlaubt sind: {allowed}."
    for key, value in args.items():
        spec = props.get(key) or {}
        kind = spec.get("type")
        if isinstance(kind, str) and not _type_ok(value, kind):
            return f"Feld '{key}' muss vom Typ {kind} sein. Erlaubt sind: {allowed}."
        enum = spec.get("enum")
        if enum is not None and value not in enum:
            return f"Feld '{key}' muss einer von {', '.join(map(str, enum))} sein."
    return None


def _schema_of(name: str) -> tuple[dict | None, bool]:
    """(Schema, bekannt?) des inneren Tools: Core-/Modul-Tool aus REGISTRY oder Plugin-Tool."""
    from hydrahive.tools import REGISTRY
    tool = REGISTRY.get(name)
    if tool is not None:
        return tool.schema, True
    from hydrahive.plugins import tool_bridge as plugin_bridge
    if name.startswith(plugin_bridge.PREFIX):
        found = plugin_bridge.schemas_for([name])
        if found:
            return found[0].get("input_schema"), True
    return None, False


def loop_signature_name(tool_use: dict) -> str:
    """Name für die Loop-Bremse und die Aktivitätsanzeige: bei run_tool der innere Name (Review #782).

    Sonst ließe sich die Endlos-Bremse umgehen, indem das Modell zwischen run_tool(x, …) und x(…) wechselt.
    """
    if tool_use.get("name") == OUTER and isinstance(tool_use.get("input"), dict):
        inner = tool_use["input"].get("name")
        if isinstance(inner, str) and inner.strip():
            return inner.strip()
    return str(tool_use.get("name") or "")


def loop_signature_input(tool_use: dict) -> dict:
    if tool_use.get("name") == OUTER and isinstance(tool_use.get("input"), dict):
        args = tool_use["input"].get("args")
        return args if isinstance(args, dict) else {}
    return tool_use.get("input", {}) or {}


def unwrap_run_tool(tool_use: dict, allowed_tools: list[str]) -> tuple[dict, str | None]:
    """(ausgepackter tool_use, Fehlertext | None). Kein ``run_tool`` → unverändert zurück.

    Bei einem Fehler enthält der zurückgegebene ``tool_use`` weiterhin den ÄUSSEREN Namen; der Runner meldet den
    Fehler als Ergebnis des Aufrufs und führt nichts aus.
    """
    if tool_use.get("name") != OUTER:
        return tool_use, None
    if OUTER not in allowed_tools:
        # Agent ohne run_tool (classic): nicht auspacken. Der Dispatcher lehnt den Aufruf dann wie jedes nicht
        # erlaubte Tool ab („für diesen Agent nicht erlaubt“) – exakt wie vor dem Katalog (K7, Review #782).
        return tool_use, None
    raw = tool_use.get("input") or {}
    inner = raw.get("name") if isinstance(raw, dict) else None
    args = raw.get("args", {}) if isinstance(raw, dict) else None
    if args is None:
        args = {}
    if not isinstance(inner, str) or not inner.strip():
        return tool_use, "run_tool braucht den Namen des Werkzeugs: run_tool(name=\"…\", args={…})."
    inner = inner.strip()
    if inner in FORBIDDEN_INNER:
        return tool_use, f"'{inner}' lässt sich nicht über run_tool aufrufen."
    if inner not in allowed_tools:
        return tool_use, f"Tool '{inner}' für diesen Agent nicht erlaubt."
    from hydrahive.mcp import tool_bridge as mcp_bridge
    if inner.startswith(mcp_bridge.PREFIX):
        # MCP bleibt in Stufe 1 klassisch (Spec D3): MCP-Tools direkt aufrufen, nicht über run_tool.
        return tool_use, f"'{inner}' ist ein MCP-Werkzeug – bitte direkt aufrufen, nicht über run_tool."
    schema, known = _schema_of(inner)
    if not known:
        return tool_use, f"Tool '{inner}' ist nicht mehr vorhanden."
    problem = check_args(schema, args)
    if problem:
        return tool_use, f"Argumente für '{inner}' passen nicht zum Schema: {problem}"
    return {**tool_use, "name": inner, "input": args, "via": VIA}, None
