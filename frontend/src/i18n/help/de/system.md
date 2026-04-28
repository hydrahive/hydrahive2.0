# System

## Was ist das?

Der System-Tab ist deine **Diagnose-Zentrale**. Hier siehst du auf einen Blick ob alles läuft, wie viele Ressourcen genutzt werden, und wo Daten liegen. Refresht alle 10 Sekunden automatisch.

## Was kann ich hier tun?

- **Health-Status** prüfen — DB, LLM, Workspaces, Disk
- **Live-Stats** beobachten — Agents, Projekte, Sessions, Messages, Tool-Calls, DB-Größe
- **Pfade einsehen** — wo liegt Data, Config, DB
- **Uptime tracken** — seit wann läuft das Backend

## Wichtige Begriffe

- **Health-Check** — automatischer Test pro Service. Grün = OK, Rot = Problem.
- **Compactions** — Anzahl der durchgeführten Session-Compactions
- **Tool-Calls Success-Rate** — wie viele Tool-Aufrufe erfolgreich waren

## Health-Checks im Detail

| Check | Was wird geprüft | Was tun bei Rot |
|---|---|---|
| **DB** | SQLite-Datei lesbar/schreibbar | Disk-Space prüfen, Datei-Permissions |
| **LLM** | LLM-Config existiert + Default-Modell + Provider | LLM-Tab → Config setzen |
| **Workspaces** | `data/workspaces/` schreibbar | Permissions prüfen, Disk-Space |
| **Disk** | >5% Speicher frei | Aufräumen oder größere Disk |

## Schritt-für-Schritt

### Wenn etwas nicht funktioniert

1. **System-Tab** öffnen
2. Health-Bar oben prüfen — alle 4 grün?
3. Falls Rot: Detail-Text gibt Hinweis
4. Backend-Log prüfen: `tail -f /tmp/hh2-backend.log`
5. Falls weiterhin Probleme → Backend neu starten via `dev-start.sh`

### Speicher-Verbrauch im Auge behalten

- **DB-Größe** — wächst mit jeder Message. Bei mehreren Tausend Messages langsam (DB-VACUUM kommt später).
- **Tool-Calls** — bei vielen Tool-Calls hilft Compaction (Chat → Compact-Button)

## Typische Fehler

- **DB rot mit `disk full`** — Disk voll, Platz schaffen
- **LLM rot mit `Kein Default-Model`** — LLM-Tab → Modell auswählen, speichern
- **Workspaces rot mit `Verzeichnis fehlt`** — Backend hat ohne Schreibrechte gestartet, mit korrekten ENV-Vars neu starten

## Tipps

- **Ältere Sessions löschen** wenn sie nicht mehr gebraucht werden — schrumpft die DB
- **System-Tab als erste Anlaufstelle** bei Problemen — meist ist die Antwort dort sichtbar
- **Auto-Refresh ausnutzen** — mehrere Browser-Tabs auf System öffnen tracked nichts zusätzlich, ein Tab reicht
