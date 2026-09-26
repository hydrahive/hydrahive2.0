# Plan: Lokale Design-Konsistenz für Legacy-Routen

## Ziel

Tickets, RoM-Server, Scratchpad, Werkstatt, Video-Editor und Hilfe sollen sich in die aktuelle Cockpit-Designsprache einfügen. Funktionalität und API-Verträge bleiben erhalten; geändert werden Layout-Chrome, visuelle Struktur, responsive Verhalten und sichtbare Legacy-Marker.

## Architekturentscheidung

Die Cockpit-Migration erfolgt explizit pro Route. Ein reines `cockpit: true`-Flag reicht nicht, weil die Seite zusätzlich `CockpitTopbar`/`CockpitShell` und passende Größen- bzw. Overflow-Regeln braucht. Legacy-Theme-Templates werden für diese Zielrouten nicht mehr als Seiten-Wrapper verwendet.

## Dateien / Bereiche

- `frontend/src/App.tsx` — Werkstatt-/Hilfe-Routen in Cockpit-Seitenpfad überführen.
- `frontend/src/shared/Layout.tsx` — Cockpit-Routenliste nur dort erweitern, wo die Seite einen eigenen Cockpit-Chrome besitzt.
- `frontend/src/features/cockpit/CockpitTopbar.tsx` — gemeinsame Navigation bleibt zentrale Quelle.
- `frontend/src/features/cockpit/WerkstattCockpitPage.tsx` — Cockpit-Wrapper für Chat/Werkstatt.
- `frontend/src/features/help/HelpPage.tsx` — Hilfe-Seite in Cockpit-Shell überführen.
- `frontend/src/modules/tickets/*` — Tickets-Nav und Seite in Cockpit-Shell überführen.
- `frontend/src/modules/rom/*` — RoM-Seite in Cockpit-Shell überführen.
- `frontend/src/modules/scratchpad/*` — Scratchpad-Seite in Cockpit-Shell überführen.
- `frontend/src/modules/videoeditor/*` — Video-Editor-Seite in Cockpit-Shell überführen.
- `frontend/src/i18n/help/*` — Inhalte bleiben fachlich unverändert; nur Darstellung/Route ändert sich.

## Implementierungsreihenfolge

### Task 1: Gemeinsame Shell-Verträge und Routing

- [ ] Zielrouten und `cockpit:true`/Core-Cockpit-Pfade vollständig festlegen.
- [ ] Werkstatt-Wrapper als eigene Komponente erstellen, damit `ChatPage` nicht direkt Legacy-Theme rendert.
- [ ] Hilfe als Cockpit-Route rendern.
- [ ] Test: alle Zielrouten laden, CockpitTopbar vorhanden, kein horizontaler Overflow.
- [ ] Commit: `refactor(layout): route legacy workspaces through cockpit shell`

### Task 2: Tickets

- [ ] Tickets-Seite mit `CockpitTopbar` und `CockpitShell` integrieren.
- [ ] Bestehende Ticketliste, Detailansicht, Teamsettings, Notifications und Formulare funktional unverändert lassen.
- [ ] Legacy-Hintergrund-/Abstandsregeln durch Cockpit-Panels ersetzen.
- [ ] Browser-Smoke: Liste laden, neues Ticket öffnen, Detail öffnen, Navigation zurück.
- [ ] Commit: `refactor(tickets): align page with cockpit design`

### Task 3: Scratchpad und RoM

- [ ] Beide Seiten in Cockpit-Shell integrieren.
- [ ] `box`/`rgbFor`/alte Zufallsfarben aus dem sichtbaren Hauptbereich entfernen.
- [ ] Zustände, Speichern, Preview, Serverstatus, Tabs und Toasts unverändert testen.
- [ ] Commit: `refactor(workspaces): align scratchpad and rom with cockpit design`

### Task 4: Hilfe

- [ ] Hilfe-Navigation als Cockpit-Seitenpanel gestalten.
- [ ] Markdown-Darstellung, Sprachwechsel, Loading/Error-Zustände beibehalten.
- [ ] Hilfe aus CockpitTopbar und direkter `/help`-Route visuell konsistent machen.
- [ ] Commit: `refactor(help): align help page with cockpit design`

### Task 5: Werkstatt/Chat

- [ ] ChatPane in einen Cockpit-Wrapper setzen, ohne Chat-Funktionalität oder Drei-Panel-Layout zu brechen.
- [ ] Sessionliste, Workspacepanel, Composer, Toolbestätigungen und Overlays prüfen.
- [ ] Desktop, schmale Breite und Panel-Collapse testen.
- [ ] Commit: `refactor(chat): align werkstatt with cockpit shell`

### Task 6: Video-Editor

- [ ] Video-Editor-Übersicht in Cockpit-Shell überführen.
- [ ] Timeline/Editor als komplexen Unterbereich separat behandeln; keine Funktionalitätsänderung.
- [ ] Projektwahl, Upload, Browse, Editor öffnen/zurück und Export-Smoke testen.
- [ ] Commit: `refactor(videoeditor): align workspace with cockpit design`

### Task 7: Rest-Audit und Abschluss

- [ ] Alle Frontend-Routen gegen die Designmatrix prüfen.
- [ ] Keine unbeabsichtigten Legacy-Theme-Wrapper auf Zielrouten.
- [ ] `tsc`, Produktionsbuild, fokussierte Browser-Smokes und Overflow-Prüfung.
- [ ] Unabhängige bestehende Arbeitsänderungen nicht anfassen.
- [ ] Abschlussbericht und ggf. Folgeaufgaben für bewusst noch nicht migrierte Seiten.

## Akzeptanzkriterien

- [ ] Tickets, RoM, Scratchpad, Werkstatt, Video-Editor und Hilfe zeigen den gleichen Cockpit-Chrome wie die aktuellen neuen Bereiche.
- [ ] Keine sichtbare alte Legacy-Topnav/Theme-Hülle auf diesen Zielrouten.
- [ ] Bestehende Funktionen und API-Aufrufe bleiben erhalten.
- [ ] Navigation zwischen Zielrouten bleibt konsistent.
- [ ] Desktop und 390px/kleine Breite ohne horizontales Überlaufen.
- [ ] Hilfe bleibt aus dem Header erreichbar und zeigt kontextbezogene Inhalte.
- [ ] Produktionsbuild und fokussierte Browser-Smokes sind grün.

## Nicht in diesem Plan

- Keine pauschale globale CSS-Überschreibung aller Legacy-Klassen.
- Keine Abschaltung oder Entfernung des Theme-Systems für bewusst noch nicht migrierte Seiten.
- Keine API-/Datenmodelländerungen.
- Keine Änderungen an der Chat-/Video-/Ticket-Fachlogik außer zwingenden Layout-Anpassungen.
