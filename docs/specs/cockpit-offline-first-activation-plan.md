# Plan: Cockpit-Aktivierung offline-first

## Ziel
Die Cockpits sollen nicht mehr aus Dummies bestehen. Jede sichtbare Kachel wird in eine von drei Kategorien eingeordnet und entsprechend umgesetzt:

1. **Echte lokale Aktion** — funktioniert ohne Internet und ohne LLM.
2. **Lokale Navigation/Modulöffnung** — öffnet vorhandene Seiten/Module, ohne LLM-Call.
3. **Explizite KI-Aktion** — nur dort, wo der User bewusst einen Agenten/LLM startet; niemals implizit beim Klick auf normale UI.

Normale Klicks dürfen keine Chat-/LLM-Anfrage versteckt auslösen. Wenn Internet oder LLM weg ist, müssen Projekt-, Datei-, Task-, Medien-, Vault- und Admin-Grundfunktionen weiter nutzbar bleiben.

## Grundregeln

- **Offline-first:** Lesen, Schreiben, Navigieren, lokale Dateien, lokale Tasks, lokale Module, lokaler Gitea, lokale Medienlisten und lokale Systemseiten funktionieren ohne Internet.
- **LLM ist optional:** LLM darf nur als beschrifteter Button/Chat-Fläche auftauchen: „Mit Buddy fragen“, „Media-Agent starten“, „Vault-Agent fragen“.
- **Kein Auto-LLM:** Kein `onClick={() => handleSend(...)}` für normale Kacheln wie Musik, Games, Projekt öffnen, Akte, Dokumente, Admin, System.
- **Kein Fake:** Wenn etwas noch nicht aktiv ist, zeigt die UI „geplant“ oder „nicht verbunden“ und bietet keinen scheinbaren Aktionsbutton.
- **Bestehende Module zuerst:** Vor neuem Backend werden vorhandene Module/Seiten verwendet: Tasks, Scratchpad, Minigames, Boardgames, Atelier, Patientenakte, Cryptoboard, System, Extensions, Modules, Credentials.
- **Gefährliche Aktionen bleiben geschützt:** Admin/Wartung/Secrets/Backups/Restore brauchen bestehende Guards/Confirmations.

## Aktivierungs-Matrix

### Buddy
| Bereich | Aktueller Status | Zielaktion offline-first | LLM? |
|---|---|---|---|
| Modus/Stimmung | UI ohne echte Persistenz | lokale/sessionbasierte BuddyPrefs speichern, beeinflusst nur UI/Prompt-Defaults | Nein |
| Quickie „Was liegt an?“ | sendet Chat | öffnet lokale Tagesübersicht: offene Tasks + letzte Sessions + Projektstatus | Optional separat |
| Quickie „Idee merken“ | sendet Chat | Scratchpad-Notiz-Dialog öffnen/speichern | Nein |
| Quickie „Projekt öffnen“ | sendet Chat | `/projects` öffnen | Nein |
| Musik | teils echtes BuddyWidget | MusicPlayerBuddyBox als richtige Kachel, Play/Pause/Upload/Generated-Import direkt | Nein |
| Games | teils Links | direkte Links zu `/minigames` und `/boardgames`, Status/zuletzt gespielt lokal | Nein |
| Wühlkiste | Dummy | lokale Liste/Scratchpad-Sektion für gemerkte Ideen | Nein |
| Buddy-Chat | echt | bleibt bewusstes Chat-/LLM-Feld | Ja, explizit |

### Media
| Bereich | Aktueller Status | Zielaktion offline-first | LLM? |
|---|---|---|---|
| Media-Projekt | Dummy-Auswahl | lokale Projektbindung/Atelier-Projekte laden | Nein |
| Produktionsbereich | Kacheln | öffnet Atelier-Unterbereiche/Assets/Regie/Charaktere | Nein |
| Modelle | Text | lokale Modellkatalog-/Settings-Links, nur Auswahl ohne Jobstart | Nein |
| Pipeline | Anzeige | lokale Szenen-/Assetliste, Status aus Atelier/Workspace | Nein |
| Media-Agent | geplant | eigener expliziter Chatbereich/Button, keine Kachel-Autoanfrage | Ja, explizit |
| Timeline/Schnitt | Dummy | vorhandenen Videoeditor/Atelier-Composer öffnen oder „nicht installiert“ anzeigen | Nein |

### Vault
| Bereich | Aktueller Status | Zielaktion offline-first | LLM? |
|---|---|---|---|
| Patientenakte | Link | vorhandene Akte öffnen, Dokumente später mit eigener Aufgabe | Nein |
| Crypto | Link | Cryptoboard öffnen, keine Trading-Automation | Nein |
| Dokumente | geplant | lokale Dokumentenliste/Upload-Task, PDF/FTS später als Task | Nein |
| Private Notizen | Link | Scratchpad direkt öffnen/Notizdialog | Nein |
| Datamining/Memory | Links | Suchseiten öffnen; keine Suche beim Laden | Nein |
| Vault-Chat | geplant | expliziter sensibler Chat mit Kontext-Guard | Ja, explizit |
| Export/OCR/Search | teilweise Dummy | lokale Buttons nur aktiv, wenn Backend vorhanden; sonst klar „geplant“ | Nein |

### Admin
| Bereich | Aktueller Status | Zielaktion offline-first | LLM? |
|---|---|---|---|
| System/User/Module/Extensions/Plugins/Credentials | Links | vorhandene Seiten öffnen | Nein |
| Integrationen | Links | Extension-/Credential-Seiten öffnen; Status lokal/API | Nein |
| Metriken | Dummy/Roadmap | bestehende System-Status-API anzeigen, ohne breites Polling | Nein |
| Logs | geplant | vorhandene Log-/Systemkarten öffnen, später eigener Logviewer | Nein |
| Admin-Chat | geplant | expliziter Chatbereich für Analyse; keine Admin-Kachel startet LLM | Ja, explizit |
| Backup/Restore | Links | bestehende Backup-Karte/Systemseite, Confirmations bleiben | Nein |

## Implementierungsreihenfolge

### Task 1: Dummy-Audit und Typisierung
- [x] Datei `frontend/src/features/cockpit/actionRegistry.ts` anlegen.
- [x] Typen: `local-link`, `local-action`, `status-only`, `explicit-ai`.
- [x] Buddy-Quickies auf Offline-Aktionen mappen.
- [x] Test/Check: Buddy-Rail-Quickies verwenden keine `handleSend`/`chat.send`-Autoanfragen.
- Commit: `refactor(cockpit): classify cockpit actions offline first`

### Task 2: Buddy offline aktivieren
- [x] Buddy-Quickies auf echte lokale Aktionen umstellen:
  - „Projekt öffnen“ → `/projects`
  - „Idee merken“ → Scratchpad/Notizdialog oder `/scratchpad` mit klarer Übergabe
  - „Was liegt an?“ → lokale Statuskarte aus Tasks/Projektstatus, ohne LLM
- [x] Rechte Mini-Dummies entfernen oder durch echte Modulwidgets ersetzen.
- [x] Music/Games/Scratchpad als echte Links/Controls, keine Slash-Fake-Klicks.
- [x] Buddy-Chat bleibt explizit als LLM-Aktion.
- Commit: `feat(buddy): activate offline quick actions`

### Task 3: Media offline aktivieren
- [x] Media-Projekt-Auswahl aus vorhandenen Projekten/Atelier-Daten laden.
- [x] Produktionsbereich-Kacheln auf reale Atelier-/Streaming-/Music-/Videoeditor-Links verdrahten.
- [x] Pipeline zeigt lokale Projekt-/Statusdaten oder explizit erreichbare Offline-Hinweise statt Dummy-Texte.
- [x] Media-Agent als klar beschrifteter optionaler Chat, nicht als Default-Klick.
- Commit: `feat(cockpit): activate media offline actions`

### Task 4: Vault offline aktivieren
- [x] Vault-Bereiche direkt mit vorhandenen Modulen verbinden.
- [x] Dokumente/FTS/OCR als deaktivierte, klare „geplant“-Aktion solange Backend fehlt.
- [x] Datamining/Memory nur als Navigation, keine Suche beim Laden.
- [x] Vault-Chat nur explizit und mit sensibler Warnung.
- Commit: `feat(cockpit): activate vault offline actions`

### Task 5: Admin offline aktivieren
- [x] Admin-Kacheln auf vorhandene lokale Systemseiten/API-Status verbinden.
- [x] Keine gefährlichen Aktionen im Cockpit direkt ausführen; nur Seiten öffnen oder Status lesen.
- [ ] Logs/Metriken nur aus vorhandenen lokalen APIs, kein LLM.
- Commit: `feat(cockpit): activate admin offline actions`

### Task 6: Tests/Guards
- [x] Frontend-Build grün.
- [x] Statischer grep/Check: keine nicht-Chat-Kachel ruft `handleSend`, `chat.send`, `buddyApi.logCmd` auf.
- [ ] Offline-Smoke: Netzwerk/LLM nicht erforderlich für Navigation und lokale Panels.
- [ ] Staging-Smoke: `/buddy`, `/media`, `/vault`, `/admin`, `/projects` laden.
- Commit: `test(cockpit): guard offline-first actions`

## Akzeptanzkriterien
- [ ] Jede Kachel ist entweder echte lokale Aktion, Navigation, Status-only oder explizite KI-Aktion.
- [ ] Kein normaler Klick öffnet/verursacht ungefragt einen LLM-Chat.
- [ ] Mit abgeschaltetem Internet bleiben Projekte, Dateien, Tasks, Buddy-UI, Media-Links, Vault-Links, Admin-Links nutzbar.
- [ ] Wenn LLM nicht konfiguriert/online ist, sind nur die expliziten Chat-/Agent-Flächen eingeschränkt.
- [ ] Dummies sind sichtbar als „geplant“ markiert oder entfernt.

## Nicht in dieser Aktivierung
- Kein automatisches Trading, keine automatische Mediengenerierung, keine automatische Vault-Suche.
- Kein globaler „LLM macht alles“-Fallback.
- Keine neuen riskanten Admin-Aktionen ohne Confirm/Guard.
