# MCP-Server

## Was ist das?

**MCP** = Model Context Protocol, von Anthropic entwickelter Standard für externe Tool-Bereitstellung an LLMs. Statt jedes Tool selbst in HydraHive2 zu programmieren kannst du **MCP-Server** anbinden — die liefern dann Tools (Filesystem-Zugriff, GitHub-API, Datenbanken, etc.) die der Agent zusätzlich zu unseren 13 Core-Tools nutzen kann.

Ein MCP-Server kann auf drei Arten laufen:

- **stdio** — Subprocess auf deiner Maschine (z.B. via `npx` oder `uvx`)
- **streamable HTTP** — externer HTTP-Endpoint (modern, empfohlen für Remote-Server)
- **SSE** — Server-Sent Events (legacy)

## Was kann ich hier tun?

- **Server aus Vorlage hinzufügen** — 8 vorkonfigurierte (Filesystem, Memory, Git, GitHub, Time, Fetch, SQLite, Sequential-Thinking)
- **Custom-Server hinzufügen** — eigene MCP-Server mit eigenem Command/URL
- **Verbinden / Trennen** — `Connect`-Button öffnet die Verbindung und lädt Tool-Liste
- **Tools einsehen** — alle verfügbaren Tools mit Beschreibung
- **Bearbeiten** — Command, Args, Env-Variablen anpassen
- **Aktivieren / Deaktivieren** — Status-Toggle
- **Löschen**

## Wichtige Begriffe

- **Transport** — wie Server und Client miteinander reden (stdio/HTTP/SSE)
- **Server-ID** — interne Kennung, wird Bestandteil der Tool-Namen (`mcp__<id>__<tool>`)
- **Args** — Kommandozeilen-Argumente an den Server (z.B. erlaubte Verzeichnisse für Filesystem)
- **Env** — Umgebungsvariablen (z.B. `GITHUB_PERSONAL_ACCESS_TOKEN` für GitHub-Server)
- **Headers** — HTTP-Header für Auth (nur HTTP/SSE), z.B. `Authorization: Bearer ...`

## Schritt-für-Schritt

### Filesystem-Server für Projekt-Code anlegen

1. **Vorlage** klicken
2. **Filesystem** wählen
3. Pfad: z.B. `/home/till/claudeneu` (das Verzeichnis das der Agent sehen darf)
4. **Anlegen** — Server ist konfiguriert
5. Im Detail-Form: **Connect** klicken — npx lädt das Paket beim ersten Mal
6. 14 Tools erscheinen (`read_file`, `list_directory`, `search_files`, …)

### GitHub-Server mit eigenem Token

1. **Vorlage** → **GitHub**
2. PAT (Personal Access Token) eingeben — das ist der `ghp_...`- oder `github_pat_...`-Token
3. **Anlegen**, **Connect**
4. Tools wie `search_repositories`, `get_issue`, `create_pull_request` werden geladen

### Custom-HTTP-MCP-Server

1. **+ Neu**
2. ID, Name, Transport **HTTP**
3. URL: z.B. `https://your-server.com/mcp`
4. **Anlegen**
5. Optional in Edit-Form Headers ergänzen für Auth
6. **Connect**

### Server an Agent zuweisen

1. **Agenten** → Agent öffnen
2. **MCP-Server**-Sektion: gewünschte Server ankreuzen
3. **Speichern**
4. Im Chat hat der Agent jetzt die `mcp__<id>__<tool>`-Tools zur Verfügung

## Typische Fehler

- **`Verbindung fehlgeschlagen: [Errno 2] No such file or directory`** — `command` (z.B. `uvx` oder `npx`) ist nicht im PATH installiert. Lösung: Tool installieren (`pip install uv` für `uvx`, `apt install nodejs npm` für `npx`).
- **Server startet aber listet keine Tools** — manche Server brauchen explizite Args (z.B. allowed-paths). Detail-Form prüfen.
- **GitHub-Server `401 Unauthorized`** — Token hat nicht die richtigen Scopes. Mindestens `repo`, `read:user`, `read:org`.
- **Tools tauchen im Agent-Chat nicht auf** — Agent muss mit dem Server verknüpft sein UND der Server muss verbunden sein. Lazy-Connect greift sonst beim ersten Tool-Call.

## Tipps

- **Filesystem mit beschränktem Pfad** — gib nicht `/` als allowed-path an, sondern den spezifischen Projekt-Ordner
- **Sequential-Thinking-Server** für komplexe Probleme — gibt dem Agent eine "Denk-Skizze"-Funktion
- **Memory-Server (offizieller MCP)** ist anders als unser internes `read_memory`/`write_memory` — er bietet Knowledge-Graph-Funktionen mit Beziehungen
- **Mehrere Server pro Agent** sind kein Problem, alle Tools kommen zusammen
