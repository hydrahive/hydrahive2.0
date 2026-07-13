# Vollständiger Agenten-Editor im Projekt-Cockpit

## Was

Der Agenten-Editor im Projekt-Cockpit wird zum vollständigen, eigenständigen Editor ausgebaut. Er bleibt ein Cockpit-Overlay und leitet nicht auf die alten Einstellungsseiten weiter.

Der Editor erhält Reiter für:

1. **Übersicht** — Name, Status, Typ/Domain, Beschreibung, Tool-Bestätigung und Metadaten
2. **Modell** — Hauptmodell, Temperatur, maximale Output-Tokens, maximale Iterationen, Fallback-Modelle, Thinking-Budget und Thinking-Tiefe/Reasoning-Effort
3. **Prompt** — Systemprompt
4. **Tools** — Langzeitgedächtnis, Tools und MCP-Server
5. **Mail** — erscheint bei aktivierten Mail-Tools
6. **Skills** — Skills anlegen, bearbeiten und pro Agent aktivieren/deaktivieren
7. **Seele / MD-Dateien** — `identity.md`, `behavior.md` und `background.md`
8. **Erweitert** — Komprimierungsmodell, Tool-Result-Limit, Token-Reserve, Turn-Limit, Schwelle, Live-Truncation und Cache-TTL

## Warum

Das bisherige Overlay ist ein separat gebauter Mini-Editor und kann nur Name, Status, Beschreibung, Hauptmodell und Systemprompt ändern. Dadurch sind wesentliche Agentenparameter im Projekt-Cockpit nicht erreichbar. Die alten Einstellungsseiten sollen perspektivisch entfallen; das Projekt-Cockpit muss deshalb selbst vollständig sein.

## Wie

- `ProjectAgentEditOverlay` bleibt Eigentümer des Lade-, Draft-, Dirty- und Save-Zustands.
- Der Editor lädt Agent, Systemprompt, Modellkatalog, Tool-Metadaten und MCP-Server.
- Die Reiter werden als Cockpit-eigene Oberfläche aufgebaut.
- Vorhandene domänenspezifische Eingabekomponenten aus `features/agents` werden wiederverwendet; es gibt keine Abhängigkeit von `features/settings` oder `AgentFormTabs`.
- Agentenfelder werden über `PATCH /agents/{id}` gespeichert.
- Der Systemprompt wird über `PUT /agents/{id}/system_prompt` gespeichert.
- Skills und Soul-MD-Dateien behalten ihre bestehenden spezialisierten Endpunkte und eigenen Speichervorgänge.
- Backend-Berechtigungen bleiben unverändert maßgeblich; das Frontend erweitert keine Rechte.
- `disabled_skills` wird in das bestehende Agent-Update-Schema aufgenommen, damit die bereits vorgesehene Skill-Aktivierung tatsächlich persistiert.
- Löschen bleibt außerhalb dieses Umbaus, da das bisherige Cockpit-Overlay nur Bearbeiten angeboten hat.

## Akzeptanzkriterien

- Im Projekt-Cockpit sind maximale Iterationen und maximale Tokens editierbar.
- Alle oben aufgelisteten Reiter sind erreichbar.
- `identity.md`, `behavior.md` und `background.md` können geladen und gespeichert werden.
- Systemprompt und Agentenfelder werden korrekt gespeichert.
- Mail erscheint nur, wenn der Agent `send_mail` oder `read_mail` besitzt.
- Änderungen können verworfen werden; die Schließen-Aktion verändert nichts ungespeichert.
- Das Overlay hängt nicht von der alten Settings-Seite oder `AgentFormTabs` ab.
- TypeScript-Typecheck, ESLint und Frontend-Build sind grün.

## Nicht enthalten

- Entfernen der alten Settings-Seiten
- Neue API-Endpunkte
- Änderungen am Berechtigungsmodell
- Löschen von Agenten aus dem Projekt-Cockpit
