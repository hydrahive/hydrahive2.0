# Buddy-Einstellungscockpit

## Status

Freigegeben am 2026-07-26: Option B — Buddy erhält eine eigene vollständige Einstellungsseite hinter dem vorhandenen „Buddy-Settings“-Button. Der generische Agenteneditor wird nicht eingebettet.

## Problem

`/buddy/settings` zeigt heute nur eine reduzierte Legacy-Konfiguration. Die Tool-Liste besitzt weder Metadaten noch Kategorien oder MCP-Zuweisungen, Skills fehlen vollständig und wichtige Modell-, Sicherheits- sowie Laufzeitoptionen sind nicht erreichbar. Zusätzlich filtert die Skill-API deaktivierte Skills bereits aus, obwohl das Frontend sie zum Reaktivieren anzeigen muss.

## Zielbild

Die bestehende Schaltfläche im Buddy-Cockpit öffnet weiterhin `/buddy/settings`. Dort erscheint ein eigenständiges Cockpit im HydraHive-Design mit sieben Bereichen:

1. **Persönlichkeit** — Name, Charakter-Neuwahl, Sprache und Ton.
2. **Kontext** — persönliche dauerhafte Hinweise mit klarer Warnung, dass Änderungen eine neue Buddy-Session starten.
3. **Modelle** — Hauptmodell, Fallback-Modelle, Temperatur, Max-Tokens, Thinking-Budget und Reasoning-Effort.
4. **Tools** — durchsuchbarer und kategorisierter vollständiger Tool-Katalog mit Beschreibungen; derzeit nicht geladene, aber zugewiesene Tools bleiben sichtbar. Zusätzlich MCP-Server, Langzeitgedächtnis und Tool-Bestätigung.
5. **Skills** — effektive Skills aus System-, Benutzer-, Projekt- und Buddy-Scope mit sichtbarer Herkunft; Skills lassen sich aktivieren/deaktivieren. Buddy-eigene Skills lassen sich anlegen, bearbeiten und löschen.
6. **Mail** — eigenes Buddy-Postfach, sichtbar sobald ein Mail-Tool aktiv ist.
7. **Erweitert** — Compaction-Modell, Trigger, Tool-Result-Limits, Reserve-Tokens, maximale Turns, maximale Iterationen und Cache-TTL.

Der rohe System-Prompt beziehungsweise Soul-Dateien werden nicht direkt bearbeitet. Persönlichkeit, Ton und Kontext bleiben die sichere Buddy-spezifische Abstraktion.

## Backend-Vertrag

### `GET /api/buddy/config`

Liefert zusätzlich zur bestehenden Konfiguration:

- `agent_id`
- vollständige Modell-/Runtime-Felder
- `mcp_servers`
- `disabled_skills`
- `require_tool_confirm`
- `longterm_memory`
- vollständige Compaction-/Cache-Felder
- `available_tools` als Metadaten (`name`, `description`, `category`)

`all_tools` bleibt vorerst kompatibel. Gespeicherte Tool-Namen, die derzeit nicht registriert sind, werden vom Frontend als „nicht verfügbar“ erhalten und angezeigt.

### `PATCH /api/buddy/config`

Akzeptiert nur Buddy-sichere, vom Eigentümer änderbare Felder. Nicht änderbar sind Owner, Typ, `is_buddy`, Projektbindung, Status und fremde Agenten. Alle Änderungen laufen weiterhin über `agent_config.update`, damit dessen Validierung und Secret-Merge gelten.

### `GET /api/skills?agent_id=…&include_disabled=true`

Liefert die effektive Skill-Menge vor Anwendung von `disabled_skills`. Der Standard bleibt rückwärtskompatibel und filtert deaktivierte Skills weiterhin aus.

## Sicherheit

- Buddy-Auflösung erfolgt ausschließlich über den authentifizierten Benutzer.
- Keine freie Agent-ID wird an den Buddy-Patch-Endpunkt übergeben.
- Tool-, MCP-, Skill- und Modellwerte werden serverseitig durch bestehende Agentenvalidierung beziehungsweise feste Pydantic-Grenzen geprüft.
- Mail-Secrets bleiben maskiert; leere Passwörter überschreiben bestehende Secrets nicht.
- System-Skills sind nur lesbar. Bearbeiten und Löschen ist nur für Buddy-eigene Skills möglich.
- Ein unbekanntes, bereits gespeichertes Tool wird sichtbar erhalten, aber nicht durch „Alle aktivieren“ neu hinzugefügt.

## Design

- `CockpitShell` und `CockpitTopbar`, keine Legacy-`box`, keine `rgbFor`-Farben und keine Indigo-/Violett-Gradienten.
- Linke, auf kleinen Displays horizontal scrollbare Bereichsnavigation; Inhalt als ruhiges Cockpit-Panel.
- Permanente Save-Bar nur bei ungespeicherten Änderungen.
- Suche, Kategorien und Zähler bei Tools und Skills.
- Fehler-, Lade-, Leer- und Erfolgszustände sind sichtbar und in DE/EN lokalisiert.

## Akzeptanzkriterien

- [ ] Der bestehende Buddy-Settings-Button öffnet das neue eigenständige Cockpit.
- [ ] Alle aktuell registrierten Core-, Modul- und Plugin-Tools sind mit Name, Beschreibung und Kategorie sichtbar.
- [ ] Bereits zugewiesene, aktuell nicht registrierte Tools bleiben sichtbar und gehen beim Speichern nicht verloren.
- [ ] MCP-Server, Langzeitgedächtnis und Tool-Bestätigung sind konfigurierbar.
- [ ] Hauptmodell, Fallbacks und Runtime-Parameter sind konfigurierbar.
- [ ] System-, Benutzer-, Projekt- und Buddy-Skills sind sichtbar; deaktivierte Skills können wieder aktiviert werden.
- [ ] Buddy-eigene Skills können im neuen Design erstellt, bearbeitet und gelöscht werden.
- [ ] Mail- und vollständige Advanced-Konfiguration sind erreichbar.
- [ ] Normale Benutzer können ausschließlich ihren eigenen Buddy bearbeiten.
- [ ] Backend-Tests, Frontend-Build, Browser-Desktop/Mobil und Security-Review sind grün.
