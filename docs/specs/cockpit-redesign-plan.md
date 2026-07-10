# Plan: Cockpit-Redesign

Stand: 2026-07-10  
Basis-Inventur: `docs/specs/cockpit-redesign-inventory.md`  
Mockups:

- `generated/mockups/cockpit-v2/index.html`
- `generated/mockups/buddy-page-v1/index.html`
- `generated/mockups/media-cockpit-v1/index.html`
- `generated/mockups/vault-cockpit-v1/index.html`
- `generated/mockups/admin-cockpit-v1/index.html`

## Ziel

HydraHive wird von verstreuten Einzelbereichen zu wenigen professionellen Cockpits umgebaut:

```text
Projekte · Buddy · Media · Vault · Admin · Hilfe
```

Der Umbau führt vorhandene Systeme zusammen. Er ersetzt nicht blind bestehende Chat-/Tool-/Projekt-/Modul-Logik.

## Nicht verhandelbare Regeln

1. Bestehenden Chat nicht neu bauen.
2. Uploads, Vibe-Coding, Tool-Calls, Tokens, Kosten, Cache, Slash Commands bleiben erhalten.
3. Aktive Projektwahl wird serverseitig pro User gespeichert.
4. Gitea ist immer das lokale Gitea aus System/Credential-Konfiguration.
5. Keine versteckten LLM-Calls beim Laden von Cockpits.
6. Neue Cockpits werden parallel zu alten Routen gebaut.
7. Umsetzung läuft über Feature-Branch und PR.

---

# Etappe 0 — Branch, PR-Grundlage, Inventur absichern

## Ziel

Arbeitsgrundlage schaffen, ohne funktionales Verhalten zu ändern.

## Dateien

- `docs/specs/cockpit-redesign-inventory.md`
- `docs/specs/cockpit-redesign-plan.md`

## Schritte

- [ ] Branch erstellen: `feat/cockpit-redesign`
- [ ] Inventur committen.
- [ ] Plan committen.
- [ ] PR als Draft erstellen.

## Akzeptanzkriterien

- [ ] Branch existiert.
- [ ] PR existiert als Draft.
- [ ] Keine App-Funktion geändert.

---

# Etappe 1 — Cockpit-Shell und neue Topbar

## Ziel

Neue Navigationsstruktur sichtbar machen, ohne alte Seiten zu löschen.

## Neue Struktur

```text
/projects  → Projekt-Cockpit
/buddy     → Buddy
/media     → Media-Cockpit
/vault     → Vault-Cockpit
/admin     → Admin-Cockpit
/help      → Hilfe
```

## Dateien voraussichtlich

- `frontend/src/App.tsx`
- `frontend/src/shared/nav-config.ts`
- `frontend/src/shared/Layout.tsx`
- `frontend/src/shared/layouts/TopnavLayout.tsx`
- neu: `frontend/src/features/cockpit/CockpitShell.tsx`
- neu: `frontend/src/features/cockpit/CockpitPanel.tsx`
- neu: `frontend/src/features/cockpit/CockpitSection.tsx`
- neu: `frontend/src/features/cockpit/CockpitOverlay.tsx`
- neu: `frontend/src/features/cockpit/index.ts`

## Schritte

- [ ] Gemeinsame Cockpit-UI-Komponenten anlegen.
- [ ] Topbar auf Zielstruktur bringen.
- [ ] Leere/leichte Routen für `/projects`, `/media`, `/vault`, `/admin` anlegen.
- [ ] Bestehende `/buddy` Route beibehalten, aber Topbar-Struktur angleichen.
- [ ] Alte Routen nicht löschen.

## Tests

- [ ] Frontend Build.
- [ ] Routing Smoke-Test: alle neuen Routen laden.
- [ ] Alte Routen laden weiter.

## Akzeptanzkriterien

- [ ] Topbar zeigt `Projekte · Buddy · Media · Vault · Admin · Hilfe`.
- [ ] Neue Routen sind erreichbar.
- [ ] Alte Seiten sind weiterhin erreichbar.
- [ ] Keine Chat-Logik wurde geändert.

---

# Etappe 2 — Serverseitige User-Preferences

## Ziel

Aktives Projekt und spätere Cockpit-Zustände serverseitig pro User speichern.

## Neue API

```http
GET /api/me/preferences
PATCH /api/me/preferences
```

## Datenmodell Vorschlag

```json
{
  "active_project_id": "...",
  "active_media_project_id": "...",
  "active_vault_scope": "private",
  "cockpit_layout": {
    "project": {
      "leftCollapsed": false,
      "rightCollapsed": false
    },
    "buddy": {
      "widgets": ["music", "games", "scratchpad", "wuehlkiste"]
    }
  }
}
```

## Dateien voraussichtlich

- neu: `core/src/hydrahive/api/routes/me_preferences.py`
- ggf. neu: `core/src/hydrahive/db/user_preferences.py`
- ggf. Migration für User Preferences
- `core/src/hydrahive/api/app.py` oder Router-Registry
- neu: `frontend/src/features/preferences/api.ts`
- neu: `frontend/src/features/preferences/useUserPreferences.ts`

## Schritte

- [ ] Backend-Storage entscheiden: DB-Tabelle bevorzugt.
- [ ] GET/PATCH implementieren.
- [ ] JSON-Felder validieren.
- [ ] Gelöschtes Projekt als Fallback behandeln.
- [ ] Frontend-Hook bauen.
- [ ] Projekt-Dropdown nutzt `active_project_id`.

## Tests

- [ ] User A/B getrennte Preferences.
- [ ] PATCH speichert nur erlaubte Felder.
- [ ] F5 behält aktives Projekt.
- [ ] Gelöschtes Projekt fällt sauber zurück.

## Akzeptanzkriterien

- [ ] Keine LocalStorage-Lösung für aktive Projektwahl.
- [ ] Aktives Projekt bleibt nach Reload erhalten.
- [ ] Preferences sind userisoliert.

---

# Etappe 3 — Chat einbettbar machen, ohne Funktion zu verlieren

## Ziel

Bestehenden Chat so kapseln, dass er in Cockpits verwendet werden kann, ohne Funktionen zu verlieren.

## Wichtige Regel

Nicht `NewChat` bauen. Bestehende Komponenten extrahieren/wiederverwenden.

## Bestand

- `ChatPage.tsx`
- `_ChatHeader.tsx`
- `_ChatBubbleThread.tsx`
- `MessageInput.tsx`
- `ToolConfirmBanner.tsx`
- `WorkspacePanel.tsx`
- `useChat.ts`
- `_assistantRuntime.ts`

## Neue Komponente Vorschlag

```tsx
<ChatPane
  mode="project" | "buddy" | "media" | "vault" | "admin"
  projectId={...}
  sessionFilter={...}
  showWorkspace={false | true}
/>
```

## Dateien voraussichtlich

- neu: `frontend/src/features/chat/ChatPane.tsx`
- angepasst: `frontend/src/features/chat/ChatPage.tsx`
- evtl. neu: `frontend/src/features/chat/SessionDropdown.tsx`

## Schritte

- [ ] ChatPage intern in wiederverwendbare `ChatPane` zerlegen.
- [ ] Header/Thread/Input/ToolConfirm 1:1 erhalten.
- [ ] Sessionliste optional als Dropdown statt linker Liste nutzbar machen.
- [ ] WorkspacePanel optional rechts separat nutzbar lassen.
- [ ] Keine zusätzliche Token-/Session-Abfrage pro Render.

## Tests

- [ ] Chat sendet Text.
- [ ] Chat sendet Datei.
- [ ] Chat sendet Bild.
- [ ] Tool-Confirm erscheint.
- [ ] Token-Meta erscheint.
- [ ] Compact funktioniert.
- [ ] Slash Commands funktionieren.
- [ ] Sessionwechsel funktioniert.

## Akzeptanzkriterien

- [ ] Bestehende `/werkstatt` Seite funktioniert weiter.
- [ ] `ChatPane` kann in Projekt-Cockpit genutzt werden.
- [ ] Kein Feature aus der Chat-Inventur fehlt.

---

# Etappe 4 — Projekt-Cockpit MVP

## Ziel

Erstes echtes Cockpit bauen: Projekt-Auswahl + Projekt-Chat + Agenten + Git/Dateien + Tasks.

## Route

```text
/projects
```

## Dateien voraussichtlich

- neu: `frontend/src/features/cockpit/project/ProjectCockpitPage.tsx`
- neu: `frontend/src/features/cockpit/project/ProjectSelector.tsx`
- neu: `frontend/src/features/cockpit/project/ProjectAgentsPanel.tsx`
- neu: `frontend/src/features/cockpit/project/ProjectGitPanel.tsx`
- neu: `frontend/src/features/cockpit/project/ProjectFilesPanel.tsx`
- neu: `frontend/src/features/cockpit/project/ProjectTasksPanel.tsx`
- nutzt: `frontend/src/features/chat/ChatPane.tsx`
- nutzt: `frontend/src/features/chat/workspace/WorkspacePanel.tsx`
- nutzt: `frontend/src/features/projects/api.ts`
- nutzt: `frontend/src/modules/tasks/*`

## Inhalt MVP

- kompaktes Projekt-Dropdown
- Projekt-Chat Mitte
- Session-Dropdown im Chat-Header
- links Agentenliste
- links Git/Gitea Status zunächst nur Anzeige
- links Modell/Tiefe aus Chat/Agent Controls
- rechts Dateien/Workspace
- rechts Projekt-Tasks

## Ausgeschlossen in MVP

- Gitea Repo erstellen
- Vault
- Media Pipeline
- Admin Cockpit

## Tests

- [ ] Projektwahl bleibt nach Reload.
- [ ] Sessions sind projektbezogen.
- [ ] Chat funktioniert im Projekt-Cockpit.
- [ ] Agentenliste zeigt projektbezogene Agenten/Spezialisten.
- [ ] Dateien öffnen Overlay.
- [ ] Git-Status lädt.
- [ ] Projekt-Tasks filtern nach Projekt.

## Akzeptanzkriterien

- [ ] Projekt-Cockpit ist nutzbar.
- [ ] Kein alter Projektbereich wird gelöscht.
- [ ] Kein Chat-Feature fehlt.

---

# Etappe 5 — Gitea lokal

## Ziel

Lokales Gitea pro Projekt-Repo verwalten.

## Anforderungen

- Gitea Host aus Systemkonfig/Credentials, nicht frei in UI.
- Token aus Credential-Store.
- Repo erstellen nur Admin/Projekt-Admin.
- Remote `gitea` hinzufügen.
- Push/Pull möglich.

## API Vorschlag

```http
GET  /api/projects/{id}/git/repos/{repo}/gitea
POST /api/projects/{id}/git/repos/{repo}/gitea/create
POST /api/projects/{id}/git/repos/{repo}/gitea/push
POST /api/projects/{id}/git/repos/{repo}/gitea/pull
```

## Dateien voraussichtlich

- `core/src/hydrahive/projects/_git_ops.py`
- neu: `core/src/hydrahive/projects/_gitea.py`
- relevante Project Routes
- `frontend/src/features/cockpit/project/ProjectGitPanel.tsx`

## Tests

- [ ] Kein Token im Response/Log.
- [ ] Fehlendes Gitea zeigt klaren Status.
- [ ] Repo-Erstellung wird gemockt getestet.
- [ ] Remote wird korrekt gesetzt.
- [ ] Rechteprüfung greift.

## Akzeptanzkriterien

- [ ] Cockpit zeigt Gitea Status.
- [ ] Repo erstellen funktioniert gegen lokales Gitea.
- [ ] Kein frei wählbarer Gitea Host im Standardflow.

---

# Etappe 6 — Buddy Cockpit

## Ziel

Buddy als lockeren Companion erhalten, aber in neue Struktur bringen.

## Route

```text
/buddy
```

## Dateien voraussichtlich

- `frontend/src/features/buddy/BuddyPage.tsx`
- `frontend/src/features/buddy/*`
- `frontend/src/modules/musicplayer/MusicPlayerBuddyBox.tsx`
- `frontend/src/modules/boardgames/components/BoardGamesBuddyBox.tsx`
- `frontend/src/modules/minigames/components/MinigamesBuddyBox.tsx`
- `frontend/src/modules/scratchpad/*`
- neu: `frontend/src/features/buddy/BuddyReactionVideo.tsx`
- neu: `frontend/src/features/buddy/reactions.ts`

## Inhalt

- Reaction-Video Slot
- Buddy-Chat vollwertig
- Musik/Games/Scratchpad/Wühlkiste Widgets
- Buddy Einstellungen erreichbar
- Widget Sichtbarkeit serverseitig persistent

## Tests

- [ ] Buddy-Chat funktioniert.
- [ ] Musik/Games Widgets rendern.
- [ ] Reaction-Video lädt lokalen Pfad.
- [ ] Buddy Settings bleiben erreichbar.
- [ ] Uploads und Slash Commands funktionieren.

---

# Etappe 7 — Media-Cockpit

## Ziel

Atelier, Videoeditor und Musikplayer als durchgehende Produktionspipeline bündeln.

## Route

```text
/media
```

## Dateien voraussichtlich

- neu: `frontend/src/features/cockpit/media/MediaCockpitPage.tsx`
- nutzt: `frontend/src/modules/atelier/*`
- nutzt: `frontend/src/modules/videoeditor/*`
- nutzt: `frontend/src/modules/musicplayer/*`

## Inhalt MVP

- Media-Projekt Auswahl
- Projektbindung
- Pipeline Idee → Regie → Assets → Clips → Schnitt
- Atelier Panels einbetten/verlinken
- Media-Agent Chat mit voller Chatfunktion
- keine automatische Generierung

## Tests

- [ ] Media-Cockpit lädt ohne Generierungsjob.
- [ ] Atelier-Bausteine erreichbar.
- [ ] Projektbindung sichtbar.
- [ ] Media-Chat funktioniert.

---

# Etappe 8 — Vault-Cockpit

## Ziel

Sensible/private Bereiche bündeln: Akte, Crypto, Dokumente, Finanzen/Notizen.

## Route

```text
/vault
```

## Dateien voraussichtlich

- neu: `frontend/src/features/cockpit/vault/VaultCockpitPage.tsx`
- nutzt: `frontend/src/modules/patientenakte/*`
- nutzt: `frontend/src/modules/cryptoboard/*`
- nutzt: `frontend/src/modules/scratchpad/*`

## Inhalt MVP

- Vault Landing mit Akte/Crypto/Dokumente/Notizen
- Vault-Chat mit voller Chatfunktion
- sensible Markierung
- keine automatische Datenweitergabe in andere Cockpits

## Ausgeschlossen initial

- vollständiges Lock/Unlock-System, falls zu groß
- Akte PDF/FTS, falls noch nicht portiert
- Finanzen-Komplettmodul

## Tests

- [ ] Vault Route geschützt nach Auth.
- [ ] Akte/Crypto erreichbar.
- [ ] Uploads mit Guards.
- [ ] Keine sensiblen Daten in normale Projektkontexte ohne Useraktion.

---

# Etappe 9 — Admin-Cockpit

## Ziel

Admin-Funktionen zusammenführen.

## Route

```text
/admin
```

## Dateien voraussichtlich

- neu: `frontend/src/features/cockpit/admin/AdminCockpitPage.tsx`
- nutzt: `features/users/*`
- nutzt: `features/system/*`
- nutzt: `features/modules/*`
- nutzt: `features/extensions/*`
- nutzt: `features/plugins/*`
- nutzt: `features/credentials/*`
- nutzt: `features/llm/*`
- nutzt: `features/mcp/*`
- nutzt: `features/skills/*`

## Inhalt MVP

- Systemstatus
- User/Rollen
- Module/Extensions/Plugins
- Credentials/Integrationen
- Logs/Wartung
- Admin-Chat mit ToolConfirm

## Tests

- [ ] AdminGuard schützt Route.
- [ ] Nicht-Admin kommt nicht rein.
- [ ] User/System/Module erreichbar.
- [ ] Gefährliche Aktionen brauchen Bestätigung.

---

# Etappe 10 — Aufräumen und alte Routen bewerten

## Ziel

Nach stabilen Cockpits entscheiden, welche alten Routen weiter direkt sichtbar bleiben.

## Schritte

- [ ] Usage prüfen.
- [ ] Alte Navigationseinträge entfernen, Routen aber behalten.
- [ ] Redirects nur wo sicher.
- [ ] Hilfe-Doku aktualisieren.

---

# PR-Testmatrix

## Chat kritisch

- [ ] Text senden
- [ ] Datei senden
- [ ] Bild senden
- [ ] Drag & Drop
- [ ] Tool Call
- [ ] Tool Confirm
- [ ] Tool Result Card
- [ ] Thinking Block
- [ ] Token/Kosten/Cache Footer
- [ ] Header Last Turn Tokens
- [ ] Compact Button
- [ ] `/compact`
- [ ] `/tokens`
- [ ] `/tools`
- [ ] `/agent`
- [ ] `/model`
- [ ] Skill Catalog
- [ ] Retry/Edit/Copy/Raw/TTS
- [ ] Sessionwechsel
- [ ] Projektbindung

## Performance/Token

- [ ] Cockpit-Load löst keinen LLM-Call aus.
- [ ] TokenMeter lädt nur bei Sessionwechsel/Send/Refresh.
- [ ] Datamining Widgets laden keine breite Suche automatisch.
- [ ] Keine Render-Loop mit Session/API-Reload.

## Security

- [ ] AdminGuard für Admin.
- [ ] Projektrechte für Projekt-Cockpit-Aktionen.
- [ ] Gitea Token nie im UI/Log.
- [ ] Vault sensible Kontexte getrennt.
- [ ] ToolConfirm bei gefährlichen Tools.

## Build

- [ ] Frontend Typecheck grün.
- [ ] Frontend Build grün.
- [ ] Backend Tests für neue APIs grün.

---

# Offene Entscheidungen vor Implementierung

1. Preferences Storage: eigene DB-Tabelle bestätigen.
2. `/projects` als Startseite oder Buddy bleibt Landing?
3. Gitea Repo-Erstellung: nur Button oder optional Auto bei Projektanlage?
4. Vault Lock/Unlock in MVP oder spätere Etappe?
5. Media-Cockpit als Core-Feature oder Modul-Route?

## Empfehlung

- Preferences: eigene DB-Tabelle.
- Landing zunächst Buddy lassen, Topbar aber neu.
- Gitea Repo-Erstellung manuell per Button.
- Vault Lock später, aber sensible Markierung sofort.
- Media-Cockpit als Core-Cockpit, nutzt Module intern.
