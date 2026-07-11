# Cockpit-Chrome P2: Apps, Benutzer und kontextuelle Hilfe

## Was

Die globale Cockpit-Topbar erhält drei klar getrennte globale Funktionen: einen App-Launcher, kontextuelle Seitenhilfe und ein Benutzer-Menü mit Profil, Einstellungen und Logout.

## Warum

Cockpit-Routen umgehen das normale Layout und verlieren dadurch zentrale globale Funktionen. Der bisherige generische Profil-Button ist kein echtes Benutzer-Menü und die globale Hilfe führt nur auf eine allgemeine Seite statt zur passenden Cockpit-Hilfe.

## Wie

- **Apps** öffnet einen kompakten Launcher aus der bestehenden zentralen Navigation und berücksichtigt Rollen.
- **Hilfe** öffnet den vorhandenen `HelpDrawer` mit einem zum Cockpit passenden Thema: Projekte → projects, Buddy → buddy, Media → atelier, Vault → patientenakte, Admin → system.
- Das Benutzer-Menü zeigt Benutzername und Rolle und bietet Profil, Einstellungen und Logout.
- Logout verwendet ausschließlich den bestehenden Auth-Store und navigiert anschließend zu `/login`.
- Auf kleinen und mittleren Displays liegen dieselben globalen Funktionen im responsiven Cockpit-Menü.
- Es entstehen keine neuen Auth-, Navigations- oder Hilfe-APIs.

## Implementierungsreihenfolge

1. App-Launcher und Benutzer-Menü als kleine Cockpit-Komponenten erstellen.
2. Kontextuelle Hilfe in die Topbar einhängen.
3. Desktop- und responsive Menüdarstellung verbinden.
4. Build, Offline-Guard, Security- und Architekturprüfung ausführen.

## Akzeptanzkriterien

- Apps sind aus jedem Cockpit erreichbar und nach Rolle gefiltert.
- Profil und Einstellungen sind erreichbar.
- Logout entfernt die bestehende Session und führt zu `/login`.
- Hilfe öffnet den vorhandenen Drawer mit passendem Thema.
- Desktop-Topbar bleibt ruhig und enthält nur globale Funktionen.
- Responsive Menüführung bleibt funktionsfähig.
- Update-Footer und Cockpit-Inhalte bleiben unverändert.

## Nicht enthalten

- Neue Apps oder Navigationsziele.
- Änderungen am Auth-Backend.
- Neue Hilfe-Engine oder neue Backend-Endpunkte.
