# Funktionsaudit: altes Design vs. Cockpits

Stand: 2026-07-11

## Methode

Verglichen wurden die letzte vollständige alte Projektverwaltung vor Commit `c34dc397` (`ProjectsPage`, `ProjectForm`, `ProjectList`) sowie die alte Navigations-/Feature-Inventur mit dem aktuellen Cockpit auf `main` nach PR #282. Bewertet wird Funktionalität, nicht optische Gleichheit.

## Blocker / sofort benötigt

### Projekte

1. **Projekt anlegen war unsichtbar.** Ursache: Aktion lag im ausgeblendeten `CockpitShell`-Header. Fix PR #283 setzt die Aktion in die sichtbare Topbar.
2. **Direkte Projekt-Basisbearbeitung fehlt im Cockpit.** Altes Design erlaubte Name, Beschreibung und Status direkt zu ändern und zu speichern. Neu gibt es nur Beschreibung als Text und einen Link zur alten Settings-Seite.
3. **Projekt löschen fehlt im Cockpit.** Altes `SettingsTab` hatte den kontrollierten Delete-Flow.
4. **Mitgliederverwaltung fehlt im Cockpit.** Altes `OverviewTab`/`MemberManager` konnte Mitglieder pflegen.
5. **Server-/VM-/Container-Zuordnung fehlt.** Altes `ServersTab` war vollständig eingebettet.
6. **Mount-/SMB-Verwaltung fehlt.** Altes `MountsTab` war vollständig eingebettet.
7. **Audit-Log fehlt.** Altes `AuditTab` zeigte sensible Projektänderungen.

Diese Funktionen existieren weiterhin unter `/settings/projects`, sind im neuen Cockpit aber nicht als Arbeitsflächen vorhanden. Der Settings-Link verhindert Totalverlust, ist jedoch keine vollständige Migration.

## Wichtig / weiterhin benötigt

### Projekte

- Projekt-Notizen bearbeiten (`NotesTab`).
- Projektstatistik: Sessions, Nachrichten, Tokens, letzte Aktivität (`StatsTab`).
- Vollständige Sessionliste mit Status/Zeit statt nur Chat-Dropdown (`SessionsTab`).
- Spezialisten-/Allowed-Specialists-Verwaltung (`SpecialistsTab`).
- Vollständige Git-Verwaltung: Clone/Init/Remote/Delete und Repo-Details. Das Cockpit zeigt Status/Tree und lokale Gitea-Aktionen, aber nicht sämtliche alte Detailflows.
- Projekt-MCP, Plugin-Overrides, Samba und weitere Projekt-Overrides aus `SettingsTab` als Cockpit-Overlay statt nur externer Link.

### Globales Cockpit

- Topbar ist auf schmalen Bildschirmen nicht responsiv; Navigation und Aktionen können überlaufen.
- Profil-Button ist kein echtes Avatar-/Logout-Menü wie im alten Layout.
- Globales Bento-/Apps-Menü fehlt auf Cockpit-Routen. Module sind daher nur über direkte Cockpit-/Settings-Links erreichbar.
- Kontextbezogene Hilfe nutzt nur `/help`; das frühere `HelpButton`-Verhalten fehlt.
- Breadcrumb/Seitentitel und Theme-Navigation sind durch die Cockpit-Topbar ersetzt; funktional okay, aber tiefe Unterseiten sind weniger klar.

### Buddy

- Reaction-Video-Registry und echte lokale Reaktionsvideos fehlen.
- Wühlkiste fehlt.
- Widget-Reihenfolge und Sichtbarkeit sind nicht vollständig serverseitig steuerbar.
- Musik/Games/Scratchpad sind gegenüber alten echten Modulen teilweise nur reduziert eingebunden beziehungsweise verlinkt.

### Media

- Arbeitsfähiger Slice ist vorhanden. Für komfortable Nutzung fehlen dennoch Drag-and-drop auf der Timeline, audiovisuelle Playhead-Vorschau, Export-Job im Hintergrund mit Abbruch/Fortschritt und Asset-Picker statt manueller Asset-ID-Eingabe.
- Regie-Datenmodell enthält Shot-Felder, das aktuelle kompakte UI bearbeitet aber noch nicht alle Felder vollständig.
- Generatoren bleiben bewusst im Atelier; das ist sicher, aber der Übergang von Regie/Prompt zu einem bestätigten Generatorjob braucht noch ein explizites Gate.

### Vault

- Vault ist weiterhin hauptsächlich ein sicherer Hub/Link-Sammlung, kein vollständiger Container.
- Vault Lock/Timeout fehlt.
- Dokumenten-Upload, PDF-Text, OCR und FTS fehlen.
- Sensibler Chat-Kontext-Guard und Audit fehlen.

### Admin

- Admin-Cockpit bündelt Links/Status, ersetzt aber noch nicht alle alten Verwaltungsseiten.
- Kompakte Logs, Rollenmodell, Integrationsübersicht und Admin-Chat-Kontext fehlen.

## Nice-to-have

- Cockpit-Aktionen und Labels vollständig i18n-fähig machen.
- Mobile Panels als Drawer statt nur Desktop-Grid.
- Empty-/Error-States vereinheitlichen.
- Overlay-Fokusfalle und Fokus-Rückgabe ergänzen.
- Cockpit-Topbar mit Avatar, Update-Indikator und Apps-Menü konsolidieren; Footer-Update bleibt als sichere Rückfallebene.

## Empfohlene Reihenfolge

1. Projektverwaltung vollständig ins Cockpit zurückholen: Basis, Mitglieder, Löschen, Server, Mounts, Audit, Notizen, Stats.
2. Globale Cockpit-Topbar funktional vervollständigen: responsive Nav, Apps/Bento, Avatar/Logout, kontextuelle Hilfe.
3. Media-UX härten: Asset-Picker, Preview, Drag-and-drop, Hintergrundexport.
4. Buddy echte Widgets/Reaction Assets.
5. Vault-Sicherheits- und Dokumentenschicht.
6. Admin-Konsolidierung.
