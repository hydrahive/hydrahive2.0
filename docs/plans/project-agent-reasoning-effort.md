# Plan: Projekt-Agent Reasoning-Tiefe

## Ziel

Projekt-Agenten besitzen einen persistenten `reasoning_effort`-Standard. Das Projekt-Cockpit speichert Modell und Tiefe gemeinsam; der Runner nutzt Session-Override vor Agenten-Standard.

## Dateien

- `core/src/hydrahive/api/routes/_agent_schemas.py` — Agentenfeld akzeptieren.
- `core/src/hydrahive/agents/config.py` und `_config_utils.py` — Feld speichern/backfillen.
- `core/src/hydrahive/runner/runner.py` — Priorität auflösen.
- `frontend/src/features/agents/types.ts`, `chat/types.ts` — Feld typisieren.
- `frontend/src/features/cockpit/project/ProjectAiSettingsPanel.tsx` — echte Werte, Dirty-State und Save.
- `core/tests/test_agent_reasoning_default.py` — Priorität und Capability validieren.

## Implementierungsreihenfolge

1. Agent-Schema und Normalisierung um `reasoning_effort` ergänzen.
2. Auflösung Session > Agent in eine testbare Helper-Funktion ziehen und testen.
3. Projektpanel an Capability-API anbinden und Modell + Tiefe gemeinsam speichern.
4. Build, fokussierte Tests und Ruff ausführen.
5. Commit, PR, CI und Merge.

## Akzeptanzkriterien

- Tiefenänderung aktiviert Speichern.
- Reload zeigt gespeicherten Agenten-Standard.
- Session-Override gewinnt; ohne Override greift Agenten-Standard.
- Modellwechsel aktualisiert erlaubte Tiefen.
- Kein unterstütztes Modell zeigt keine Attrappen-Auswahl.
