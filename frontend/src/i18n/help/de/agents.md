# Agenten

## Was ist das?

Ein Agent ist eine **Konfiguration** — keine laufende Instanz. Er besteht aus: Name, Typ, LLM-Modell, Tool-Whitelist, MCP-Server-Liste, System-Prompt und Memory. Der Agent wird "lebendig" wenn du eine Session mit ihm startest — dann liest der Runner seine Konfig und führt den Tool-Loop aus.

HydraHive2 kennt drei Agent-Typen:

- **Master** — eine Instanz pro User, automatisch beim ersten Login angelegt. Hat alle Tools, kein eingeschränkter Workspace, ist dein persönlicher Assistent.
- **Project** — pro Projekt einer, wird automatisch erstellt wenn du ein Projekt anlegst. Workspace ist auf den Projekt-Ordner beschränkt.
- **Specialist** — frei konfigurierbar für spezifische Domänen (Code-Review, Schreiben, Recherche, …). Werkzeug-Set anpassbar.

## Was kann ich hier tun?

- **Neuen Agent anlegen** mit Typ-Auswahl, Modell, Tools
- **Bestehende Agents bearbeiten** — Modell, Temperatur, Max-Tokens, Tools, MCP-Server, System-Prompt
- **Aktivieren / Deaktivieren** über Status-Dropdown im Header
- **Löschen** — entfernt Config + Memory + Workspace
- **Memory einsehen** indirekt über Tool-Calls vom Agent

## Wichtige Begriffe

- **System-Prompt** — die Anweisungen die der Agent als allererstes sieht. Definiert Persönlichkeit und Verhalten.
- **Memory** — JSON-File pro Agent (`agents/<id>/memory.json`). Agent kann via `read_memory`/`write_memory` lesen und schreiben.
- **Workspace** — Dateisystem-Bereich in dem der Agent operiert. Auto-erzeugt unter `data/workspaces/{master|projects|specialists}/<id>/`.
- **Temperature** — 0.0 = deterministisch, 1.0 = kreativ (Default 0.7).
- **Max Tokens** — Output-Limit pro Antwort. Code-Generation braucht 8000+, Konversation 2000–4000.
- **Thinking Budget** — Extended-Thinking-Tokens (nur Sonnet/Opus 4+). 0 = aus.

## Schritt-für-Schritt

### Specialist-Agent für Code-Review anlegen

1. **+ Neu** klicken
2. Typ **Spezialist**, Modell `claude-sonnet-4-6`, Name `Code-Reviewer`
3. **Anlegen** — Standard-Tools sind leer für Specialists
4. Im Detail-Form: Tools `file_read`, `file_search`, `dir_list`, `read_memory` ankreuzen
5. System-Prompt-Editor: schreibe genau was er tun soll, z.B.:
   *"Du analysierst Code auf Sicherheits-Probleme, Performance-Issues und Code-Smells. Lies erst die Datei, gib dann strukturiertes Feedback in Markdown."*
6. **Speichern**

### Master-Agent erweitern mit MCP-Server

1. Master-Agent in der Liste klicken
2. **MCP-Server**-Sektion: angelegte Server ankreuzen
3. **Speichern**
4. Im Chat hat der Agent jetzt zusätzlich `mcp__<server>__<tool>`-Tools

### Tool-Set einschränken

1. Agent öffnen
2. **Tools**-Sektion: nur die Tools ankreuzen die der Agent darf
3. Speichern — der Agent sieht beim nächsten LLM-Call nur diese Tools

## Typische Fehler

- **`Modell '...' ist nicht in der LLM-Konfiguration`** — Modell unter LLM-Konfig ergänzen oder ein bekanntes wählen.
- **`Unbekannte Tools`** — passiert nur wenn manuell in der `config.json` gepfuscht wurde.
- **Agent halluziniert was er kann** — System-Prompt klarer formulieren, Tool-Liste reduzieren.
- **Agent macht Endlosschleife** — Loop-Detection greift nach 3 identischen Calls; passiert oft bei zu kleinen `max_tokens`.

## Tipps

- **System-Prompt ist die wichtigste Schraube**. Spezifischer = besser. Beispiele für gewünschtes Verhalten reinschreiben.
- **Master-Agent nicht zu generisch halten** — auch er profitiert von einem klaren Profil ("Du bist mein persönlicher Programmier-Assistent…").
- **Specialist-Agents im Projekt nutzen** über `ask_agent` (kommt mit AgentLink) — Master delegiert spezifische Aufgaben.
