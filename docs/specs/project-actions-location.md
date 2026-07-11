# Project-Cockpit: Fachaktionen aus der globalen Topbar verlagern

## Was

Alle projektspezifischen Aktionen werden aus der globalen Cockpit-Topbar entfernt und in das linke Panel **Projekt** verlagert. Dort werden sie in **Projekt**, **Verwalten** und **Auswerten** gegliedert.

## Warum

Die globale Topbar ist mit zehn Projektaktionen überladen und vermischt globale Navigation mit fachlicher Projektverwaltung. Die Aktionen sollen dort liegen, wo das aktive Projekt ausgewählt und beschrieben wird.

## Wie

- Die globale Topbar erhält im Project-Cockpit keine `extraActions` und keinen zusätzlichen Projekt-Einstellungen-Sprung mehr.
- Im geöffneten Projektpanel stehen direkt **Neues Projekt** und **Projekt bearbeiten**.
- **Verwalten** enthält Zugriff, Server, Mounts, Git und Integrationen.
- **Auswerten** enthält Statistiken, Sessions und Audit.
- Gruppen sind kompakt auf- und zuklappbar; alle vorhandenen Handler und Overlays werden weiterverwendet.
- Ohne aktives Projekt bleiben projektgebundene Aktionen deaktiviert.

## Akzeptanzkriterien

- Die globale Topbar zeigt keine projektspezifischen Fachaktionen mehr.
- Alle bisherigen Projektaktionen bleiben im linken Projektpanel erreichbar.
- Aktionen sind klar in Verwalten und Auswerten gruppiert.
- Neues Projekt bleibt prominent erreichbar.
- Build und Cockpit-Offline-Guard sind grün.

## Nicht enthalten

- Änderungen an den Verwaltungs-Overlays oder APIs.
- Apps-, Avatar-, Logout- oder Hilfe-Funktionen der globalen Topbar.
