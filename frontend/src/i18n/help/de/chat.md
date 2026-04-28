# Chat

## Was ist das?

Der Chat ist dein zentrales Fenster zu den Agenten. Du kannst beliebig viele **Sessions** parallel führen — jede ist eine eigenständige Konversation mit einem Agenten. Sessions werden in der DB gespeichert und überleben Neustarts. Antworten kommen **live** während sie generiert werden (Streaming).

## Was kann ich hier tun?

- **Neue Session** starten — entweder direkt mit einem Agenten oder im Kontext eines Projekts
- **Mit dem Agenten reden** — der nutzt dabei Tools (Dateien lesen, Code ausführen, MCP-Server, …) und führt Aufgaben aus
- **Antwort abbrechen** — Stop-Button während Streaming
- **Compaction manuell triggern** — Compact-Button im Header
- **Token-Verbrauch beobachten** — Header zeigt letzten Turn (Input/Output/Cache) und Session-Total
- **Sessions löschen** — Mülleimer-Icon in der Liste rechts
- **Tabs umschalten** zwischen direkten Chats und Projekt-Chats

## Wichtige Begriffe

- **Session** — eine Konversation, identifiziert durch UUID
- **Turn** — eine User-Frage + Agent-Antwort (kann mehrere Tool-Iterationen enthalten)
- **Iteration** — ein einzelner LLM-Call innerhalb eines Turns
- **Compaction** — Zusammenfassen alter Messages um Tokens zu sparen
- **Streaming** — Antwort kommt zeichenweise statt am Stück
- **Tool-Use** — der Agent nutzt eines seiner Werkzeuge (z.B. `file_read`)
- **Cache (⚡)** — von Anthropic geliefert, wiederverwendete System-Prompt-Tokens (90% günstiger)

## Schritt-für-Schritt

### Erste Konversation

1. Klick **+ Neu** rechts oben in der Session-Liste
2. Wähle **Direkter Chat**, einen aktiven Agent, optional Titel
3. **Starten** klicken
4. Nachricht eingeben, Enter drücken
5. Beobachte wie Text live erscheint, Tools aufgerufen werden, Tool-Results in den Chat fließen

### Session in einem Projekt starten

1. **+ Neu** klicken
2. Wechsel auf **Im Projekt**
3. Projekt aus der Liste wählen — der Project-Agent ist automatisch verknüpft
4. **Starten** — alle file_*-Tools operieren jetzt im Projekt-Workspace

### Lange Konversation komprimieren

1. Beobachte den Token-Counter — wenn du dich der Compact-Schwelle näherst
2. **Compact**-Button im Header
3. Ältere Messages werden zu einer strukturierten Markdown-Zusammenfassung verdichtet
4. Im Chat siehst du dann einen **Compaction-Block** (orange) — klickbar für Details

### Antwort stoppen

Während der Agent streamt: **Stop**-Quadrat (rot) statt Send-Button. Klick → Anthropic-Stream wird abgebrochen, History wird neu geladen.

## Typische Fehler

- **`max_tokens (4096) erreicht`** — Antwort wurde abgeschnitten. Lösung: in **Agenten** → diesem Agent → Max Tokens auf 8192 oder höher.
- **`Loop erkannt`** — Agent ruft 3× das identische Tool. Schutz vor Endlosschleifen. Sage dem Agent klar was er anders machen soll.
- **`Verwaiste Session`** — der Agent dieser Session wurde gelöscht. Session löschen oder Agent neu anlegen.
- **`messages.X.content.0.text.parsed_output: Extra inputs`** — bereinigt sich automatisch durch Heal-Helper. Falls nicht: neue Session.
- **HTTP 502 / 500 von Anthropic** — kurzzeitige Server-Probleme. Nochmal probieren.

## Tipps

- **Cache nutzen**: Halte den System-Prompt eines Agents stabil. Bei wiederholten Sessions wird ein Großteil des Prompts gecached und kostet nur 10% normaler Tokens.
- **Tool-Whitelist**: pro Agent nur die Tools aktivieren die er wirklich braucht. Reduziert Tool-Selection-Halluzinationen.
- **Project-Agent für Code-Arbeit**: nutzt die Workspace-Isolation. Der Agent "sieht" nur Dateien im Projekt-Workspace.
