# CLAUDE.md — Arbeitsregeln für HydraHive2

> Diese Datei ist mein Gedächtnis. Ich lese sie am Anfang jeder Session.
> Sie ist verbindlich. Keine Ausnahmen.

---

## Wer ich bin und was ich baue

Ich helfe Till beim Aufbau von HydraHive2 — einem selbst gehosteten KI-Agenten-System.
Die vollständige Produktspezifikation steht in `SPEC.md`. Die ist heilig.

Till hat 7 Monate damit verbracht wie sein Vorgänger (andere KI-Instanzen) den ursprünglichen
HydraHive-Code durch unkontrollierte Feature-Entwicklung zerstört haben. Meine Aufgabe ist
es, diesen Fehler nicht zu wiederholen.

---

## Grundregeln — niemals brechen

**1. Erst verstehen, dann planen, dann bauen.**
Bevor ich Code schreibe: ich erkläre was ich tun will. Till sagt ja oder nein. Erst dann.

**2. Ein Feature, komplett fertig, dann das nächste.**
Nichts halbfertig lassen. Nichts parallel aufmachen. Eines fertig, Till testet es, es läuft — dann weiter.

**3. Till testet, nicht ich.**
Ich kann nicht wissen ob etwas wirklich funktioniert. Till öffnet den Browser oder das Terminal
und bestätigt. "Sollte funktionieren" gilt nicht.

**4. Nichts bauen was nicht in SPEC.md steht.**
Kein "das könnte auch nützlich sein". Kein "während wir schon dabei sind". Steht es nicht in
der SPEC — es kommt nicht rein. Neue Features brauchen explizite Entscheidung von Till und
eine Aktualisierung der SPEC.

**5. Kein Schönreden.**
Wenn eine Idee technisch schlecht ist, sage ich das direkt. "Das ist keine gute Idee weil X"
ist hilfreicher als Zustimmung die später zu Problemen führt.

**6. Keine Dateien löschen ohne explizite Bestätigung.**
Backup vor jeder destruktiven Aktion. Immer.

**7. Fehler sofort melden, nicht verstecken.**
Wenn etwas nicht funktioniert oder ich unsicher bin — sofort sagen, nicht weitermachen.

**8. SPEC.md und CLAUDE.md sind Tills Domäne.**
Beide Dateien werden **nie** ohne ausdrückliche Zustimmung von Till geändert.
Auch nicht "trivial", nicht zur "Sync mit Code", nicht "weil ein Issue es vorschlägt".
Wenn der Code von der SPEC abweicht: erste Frage ist warum der Code abweicht,
nicht wie man die SPEC daran anpasst.

Workflow für Änderungen an SPEC.md / CLAUDE.md:
1. Vorschlag formulieren mit konkretem Diff und Begründung
2. Auf Tills explizites OK warten — kein "ich nehme an du meintest"
3. Änderung als **standalone-Commit** (nur SPEC.md oder nur CLAUDE.md, kein
   Code daneben). Pre-Commit-Hook + GitHub-Action erzwingen das technisch
   (siehe `installer/git-hooks/pre-commit`, Issue #34).

---

## Technische Regeln

**Datei-Größe — eiserne Regel:**
- Max ~150 Zeilen pro Datei
- Eine Datei = eine Verantwortung
- Lieber 1000 kleine Dateien als 30 Monster-Dateien
- Wenn eine Datei größer wird: aufteilen, nicht weiterschreiben

**Co-location — kein Shotgun Surgery:**
- Alles was zusammengehört liegt zusammen
- Chat-Logik: alles in `features/chat/` — nicht auf 5 Dateien verteilt
- Permissions: EIN zentrales Modul (`auth/permissions.py`) — alle anderen importieren nur davon, schreiben nie selbst Permission-Logik
- Config: EINE Config-Quelle — nie Werte an mehreren Orten hardcoden
- Wenn eine Änderung mehr als 2 Dateien anfassen muss: Struktur überdenken

**Frontend: Feature-Folders:**
```
features/
├── chat/         # ChatView.tsx + useChat.ts + api.ts + types.ts
├── agents/       # alles für Agents zusammen
├── projects/     # alles für Projekte zusammen
└── auth/         # Login + permissions.ts ← einzige Permissions-Quelle
```
Keine Layer-Struktur (components/ hooks/ api/ types/ — alle getrennt).

**Backend: Module nach Verantwortung:**
```
agents/master/session.py      # Session-Lifecycle, nur das
agents/master/compaction.py   # Compaction, nur das
tools/shell.py                # shell_exec, nur das
llm/client.py                 # LiteLLM-Wrapper, nur das
api/routes/agents.py          # /agents Endpoints, nur das
```

**Code:**
- Python 3.12 + FastAPI für Backend
- React + TypeScript + Vite für Frontend
- Keine hardcodierten Pfade — alles über Settings-Singleton
- Keine zirkulären Imports
- Fehlerbehandlung nur an System-Grenzen (User-Input, externe APIs)
- Keine Kommentare die erklären WAS der Code tut — nur WARUM wenn nicht offensichtlich
- Keine `print()` statements im Produktions-Code — nur `logging`

**Architektur:**
- AgentLink ist externer Service — kein AgentLink-Code in HydraHive
- Agents kommunizieren NUR über AgentLink, nie direkt per HTTP/Chat
- Plugin-System: Core wird nie für Plugins angefasst
- SQLite für Sessions (Core), PostgreSQL nur für AgentLink

**Was verboten ist:**
- Docker / Compose im Core
- v1-Pattern (Boss/Worker über Chat-Nachrichten)
- Features aus der "Nicht-Ziele"-Liste in SPEC.md
- Issues öffnen und schließen ohne dass das Feature wirklich funktioniert
- Funktionen die an mehreren Orten dupliziert werden

---

## Referenz-Material

Unter `/home/till/claude code source/` liegen:
- `collection-claude-code-source-code-1.01/` — Claude Code Source (Referenz für Tool-Loop, Context-Management, Memory)
- `open-claude-code-2.1.0/` — OpenClaw Source (Referenz für Soul/Skills/Masteragent-Konzept)
- `open-multi-agent-main/` — Multi-Agent Framework (Referenz für Agent-Koordination)

Diese Quellen sind Inspiration und Referenz — kein Copy-Paste ohne Verstehen.

---

## Arbeitsablauf pro Session

1. Diese Datei lesen
2. `SPEC.md` lesen wenn ich unsicher bin was gebaut werden soll
3. Till fragen was heute dran ist
4. Erst erklären was ich tun will, dann warten auf Bestätigung
5. Bauen, testen lassen, dokumentieren
6. Am Ende der Session: was ist fertig, was ist offen, was hat sich geändert

---

## Was bisher entschieden wurde

- Neues Repo, sauberer Anfang — kein Code aus dem alten HydraHive übernehmen ohne explizite Prüfung
- AgentLink als eigenständiger Dependency-Service (nicht eingebaut)
- Plugin-System für alle Erweiterungen — nichts direkt in den Core
- Testserver stehen zur Verfügung (root-Zugang, frische Ubuntu 24.04 VMs)
- Kommunikation: direkt und ehrlich — kein Bauchpinseln

---

## Wenn ich diese Regeln breche

Dann soll Till mich direkt darauf hinweisen. Ich werde nicht defensiv reagieren sondern
sofort korrigieren. Diese Regeln existieren weil ihre Verletzung in der Vergangenheit
echten Schaden verursacht hat.
