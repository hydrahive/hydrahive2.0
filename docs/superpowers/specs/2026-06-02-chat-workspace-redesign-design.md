# Chat Workspace Redesign — Design Spec

**Datum:** 2026-06-02
**Status:** Genehmigt (Design-Phase)
**Rollback-Tag:** `pre-chat-workspace-redesign` (Commit 57e63d7d)

## Ziel

Den **normalen Chat** (`/werkstatt` bzw. `ChatPage`) von einem 2-Spalten-Layout (Chat + Sessions-Sidebar)
auf ein **Drei-Panel-Layout** umbauen, inspiriert von [hermes-webui](https://github.com/nesquena/hermes-webui):

- **Links:** Sessions-Liste (Suche, nach Datum gruppiert) + Footer mit Agent-Auswahl, Modell-Picker, Reasoning-Tiefe
- **Mitte:** Chat-Transcript + Eingabefeld + Quick-Action-Pills
- **Rechts:** Workspace-Panel mit Dateibaum, inline-Editor und Git-Integration

**Buddy bleibt unverändert.** Nur der normale Chat wird umgebaut.

Der Code wird **neu geschrieben und an den HH2-Stack angepasst** (React/TypeScript/Vite, FastAPI).
Kein Code aus hermes-webui wird übernommen — nur Design und Funktionsweise.

## Nicht-Ziele

- Buddy anfassen
- Bestehende Chat-Logik (SSE-Streaming, Tool-Cards, Compaction) neu schreiben — die wird nur umarrangiert
- Multi-File-Tabs im Editor (erstmal eine Datei zur Zeit)
- Git-Branch-Wechsel aus dem Panel (Agent oder Terminal macht das)

## Layout-Entscheidungen (alle bestätigt)

| Frage | Entscheidung |
|---|---|
| Workspace-Pfad | **Agent-Workspace only** — `workspace_for(agent)`, kein Override (Sicherheit + einfache Validierung) |
| Datei-Bearbeitung | **B** — inline Editor im Panel (lesen + schreiben) |
| Git-Umfang | **B** — Status + Diff + Stage + Commit direkt aus dem Panel |
| Panel-Kollaps | **A** — beide Seitenpanels einzeln ein-/ausklappbar |
| Modell + Tiefe | Footer der **Sessions-Leiste unten links**, nicht im Chat-Header |
| Quick-Action-Pills | Unter dem Eingabefeld (wie bisher), `model`-Pill entfällt (sitzt jetzt links) |

## Architektur

### Feature-Ordnerstruktur (Approach B — Feature-Folder)

```
features/chat/
├── ChatPage.tsx              ← schlank, orchestriert nur das Layout
├── layout/
│   ├── ThreePanelLayout.tsx  ← Spalten-Grid + Kollaps-Logik
│   └── CollapsiblePanel.tsx  ← wiederverwendbarer Panel-Wrapper (links/rechts)
├── workspace/                ← NEU
│   ├── WorkspacePanel.tsx    ← Dach: Tabs (Files/Git/Editor) + Pfad-Switcher
│   ├── FileTree.tsx          ← Dateibaum, lazy-loaded pro Ordner
│   ├── FileEditor.tsx        ← inline Editor (CodeMirror 6)
│   ├── GitPanel.tsx          ← Status + Diff + Stage + Commit
│   ├── useWorkspace.ts       ← State: aktiver Pfad, offene Datei, Git-Status
│   └── api.ts                ← Workspace/Git-API-Client
├── SessionList.tsx           ← erweitert: Footer mit Modell + Tiefe
├── _Thread.tsx               ← unverändert
└── … (bestehende Dateien unverändert)
```

Jede neue Datei bleibt unter ~200 Zeilen (HH2-Regel). Wenn `WorkspacePanel` oder `GitPanel`
zu groß wird, weiter aufteilen (z.B. `GitDiffView.tsx`, `GitCommitForm.tsx`).

### Komponenten-Verantwortlichkeiten

**`ThreePanelLayout.tsx`** — rendert drei Spalten als Flexbox. Hält die Kollaps-States
(`leftOpen`, `rightOpen`) und gibt Toggle-Callbacks an die Panels. Persistiert die States
in `localStorage` (Schlüssel `hh2.chat.panels`), damit die Aufteilung über Reloads bleibt.

**`CollapsiblePanel.tsx`** — generischer Wrapper. Props: `side` ("left"|"right"), `open`,
`onToggle`, `width`, `children`. Im eingeklappten Zustand 32px Streifen mit Pfeil-Button.

**`WorkspacePanel.tsx`** — Dach des rechten Panels. Drei Tabs (Files / Git / Editor) +
Pfad-Anzeige (read-only). Wurzel = `workspace_for(agent)` des aktiven Agenten, kein Override.

**`FileTree.tsx`** — rekursiver Dateibaum. Lädt Ordnerinhalte lazy beim Aufklappen
(`GET /api/workspace/tree?path=…`). Zeigt Git-Status-Marker (M/A/D) pro Datei.
Klick auf Datei öffnet sie im Editor-Tab.

**`FileEditor.tsx`** — CodeMirror-6-Editor. Lädt Dateiinhalt (`GET /api/workspace/file`),
speichert zurück (`PUT /api/workspace/file`). Speichern-Button + Dirty-Indicator.
Syntax-Highlighting nach Dateiendung.

**`GitPanel.tsx`** — Git-Status-Liste (geänderte/neue/gelöschte Dateien), Diff-Vorschau
pro Datei, Stage/Unstage-Checkboxen, Commit-Message-Feld + Commit-Button.

**`useWorkspace.ts`** — zentraler State-Hook: aktiver Pfad, geöffnete Datei, Editor-Inhalt,
Dirty-Flag, Git-Status. Polling des Git-Status alle paar Sekunden (wie bei VMs/Containers).

**`SessionList.tsx`** (erweitert) — bekommt einen Footer-Bereich:
Agent-Selector (bestehend, nur verschoben) + `ModelPicker` + `ReasoningEffortPill`.
Letztere zwei werden aus dem `_ChatHeader.tsx` hierher verschoben.

### Backend — neue API-Endpunkte

Es gibt **keine** generischen Workspace-File- oder Git-Status-Endpunkte. Neu nötig
(neue Route-Datei `api/routes/workspace.py`, prefix `/api/workspace`):

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/workspace/tree?path=` | Ordnerinhalt (eine Ebene, lazy) |
| GET | `/api/workspace/file?path=` | Dateiinhalt lesen |
| PUT | `/api/workspace/file` | Dateiinhalt schreiben |
| GET | `/api/workspace/git/status?path=` | Git-Status (geänderte Dateien, Branch) |
| GET | `/api/workspace/git/diff?path=&file=` | Diff einer Datei |
| POST | `/api/workspace/git/stage` | Datei(en) stagen/unstagen |
| POST | `/api/workspace/git/commit` | Commit mit Message |

**Sicherheit (KRITISCH):** Alle Pfade müssen serverseitig gegen die erlaubte Wurzel
validiert werden (Path-Traversal-Schutz). Erlaubte Wurzel = **ausschliesslich**
`workspace_for(agent)` des anfragenden Users — kein konfigurierbarer Override, kein
Zugriff ausserhalb. `require_auth` + Owner-Check auf jeden Endpunkt. Symlinks auflösen
(`Path.resolve()`) und erneut gegen die Wurzel prüfen (kein Entkommen über Links).
Jeder Pfad-Parameter wird relativ zur Wurzel interpretiert; `..`-Segmente nach dem
Resolve, die ausserhalb der Wurzel landen, geben 403.

### Datenfluss

1. User wählt Session links → `ChatPage` setzt `activeId` → Chat lädt (unverändert)
2. `WorkspacePanel` liest Default-Pfad aus aktivem Agenten → `FileTree` lädt Wurzel
3. User klickt Datei → `useWorkspace` lädt Inhalt → `FileEditor` zeigt sie
4. User editiert + speichert → `PUT /file` → Git-Status pollt → Marker erscheint im Tree
5. User wechselt zu Git-Tab → `GitPanel` zeigt Status + Diff → Stage → Commit

### Fehlerbehandlung

- File-API: 403 bei Pfad ausserhalb Wurzel, 404 bei nicht existent, 413 bei zu großer Datei
- Editor: Speichern-Fehler zeigt Toast, Inhalt bleibt erhalten (kein Datenverlust)
- Git: Commit-Fehler (z.B. nichts gestaged) zeigt klare Meldung im Panel
- Workspace ohne Git-Repo: Git-Tab zeigt "Kein Git-Repository" statt Fehler

### i18n

Neuer Namespace `workspace` (de/en) für alle neuen UI-Strings. Bestehende Chat-Strings
bleiben im `chat`-Namespace.

## Phasen (für den Implementierungsplan)

1. **Layout-Gerüst** — `ThreePanelLayout` + `CollapsiblePanel`, ChatPage umstellen,
   Modell+Tiefe in SessionList-Footer verschieben. Workspace-Panel erstmal leer/Platzhalter.
   → Till testet: 3 Spalten, Kollaps funktioniert, Chat läuft wie vorher.
2. **File-Browser (read-only)** — Backend `tree` + `file` (GET), `FileTree` + `FileEditor`
   (nur lesen). Path-Traversal-Schutz + Tests.
   → Till testet: Dateibaum lädt, Datei-Vorschau funktioniert.
3. **Editor (schreiben)** — `PUT /file`, Speichern im `FileEditor`, Dirty-Indicator.
   → Till testet: Datei bearbeiten + speichern.
4. **Git-Integration** — Backend `git/status` + `diff` + `stage` + `commit`, `GitPanel`.
   → Till testet: Status sehen, Diff, Stagen, Committen.
5. **Politur** — Polling-Tuning, i18n vollständig, localStorage-Persistenz, mobile Fallback.

Jede Phase ist eigenständig testbar und wird einzeln gepusht (HH2-Regel: ein Feature komplett fertig).

## Risiken

| Risiko | Mitigation |
|---|---|
| Path-Traversal / Datei-Lesezugriff ausserhalb Workspace | Serverseitige Wurzel-Validierung + Symlink-Auflösung + security-reviewer vor Merge |
| Monaco ~5 MB Bundle | Dynamic Import, nur beim Öffnen des Editor-Tabs geladen; initiales Laden unberührt |
| Monaco Web-Worker mit Vite fummelig | Vite `?worker`-Import-Pattern; in Phase 3 isoliert testen bevor Editor scharf geschaltet wird |
| Git-Status-Polling belastet Server | Intervall wie VMs (4s), nur wenn Git-Tab offen |
| ChatPage wird beim Umbau instabil | Phase 1 ändert nur Layout, Chat-Logik unangetastet; Till testet nach jeder Phase |
| Mobile: 3 Panels passen nicht | Auf Mobile nur Chat sichtbar, Panels als Slide-over (wie bestehende Sidebar) |

## Tech-Entscheidungen

- **Editor:** Monaco (VS-Code-Editor) — vollwertig für Programmierer: IntelliSense,
  Diff-View, Multi-Cursor, TS-Sprachverständnis. ~5 MB Bundle, daher **dynamic import**
  (`await import`) — Kosten fallen nur an wenn der Editor-Tab geöffnet wird, nicht beim
  initialen Laden. Web-Worker-Setup über Vites `?worker`-Import.
- **Git im Backend:** bestehende `_git_ops`-Helfer wiederverwenden wo möglich, aber
  workspace-scoped statt project-scoped (eigene Pfad-Validierung)
- **State:** lokaler `useWorkspace`-Hook, kein globaler Store (Workspace-State ist chat-lokal)
- **Persistenz:** Panel-Kollaps-States in `localStorage`
