"""JSON-Schemas der Datamining-Werkzeuge (ausgelagert aus datamining.py wegen Länge)."""

_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query":      {"type": "string", "description": "Suchbegriff"},
        "event_type": {"type": "string", "description": "Optional: user_input|assistant_text|tool_call|tool_result"},
        "agent_name": {"type": "string", "description": "Optional: nur Events dieses Agents"},
        "from_date":  {"type": "string", "description": "Optional: ISO-Datum z.B. 2026-01-01"},
        "to_date":    {"type": "string", "description": "Optional: ISO-Datum"},
        "limit":      {"type": "integer", "default": 20, "description": "Max. Ergebnisse (1-50)"},
    },
    "required": ["query"],
}

_SEMANTIC_SCHEMA = {
    "type": "object",
    "properties": {
        "query":      {"type": "string", "description": "Semantische Suchanfrage — findet inhaltlich Ähnliches"},
        "event_type": {"type": "string"},
        "agent_name": {"type": "string"},
        "limit":      {"type": "integer", "default": 10},
    },
    "required": ["query"],
}

_TODAY_SCHEMA = {
    "type": "object",
    "properties": {
        "date": {"type": "string", "description": "ISO-Datum (default: heute)"},
    },
}

_TIMELINE_SCHEMA = {
    "type": "object",
    "properties": {
        "from_date":   {"type": "string", "description": "ISO-Datum z.B. '2025-11-01' (default: letzte 7 Tage)"},
        "to_date":     {"type": "string", "description": "ISO-Datum (default: heute)"},
        "agent_name":  {"type": "string", "description": "Optional: nur Sessions dieses Agents"},
        "sort":        {"type": "string", "enum": ["date", "activity"],
                        "description": "Sortierung: 'date' = neueste zuerst (default), 'activity' = meiste Events zuerst"},
        "limit":       {"type": "integer", "default": 200, "description": "Max. Sessions"},
    },
    "required": [],
}
