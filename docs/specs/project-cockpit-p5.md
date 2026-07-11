# Project-Cockpit P5: Audit, Statistiken und Sessions

## Was

Das Project-Cockpit erhält drei projektbezogene Arbeitsflächen:

- **Statistiken** mit Anzahl Sessions, aktiven Sessions, Nachrichten, Tokens und letzter Aktivität.
- **Sessions** mit der vollständigen vorhandenen Projekt-Sessionliste und direkter Navigation in die Werkstatt.
- **Audit** mit Projektaktivitäten sowie Aktions- und Benutzerfilter.

## Warum

Diese Daten existieren bereits in den Projekteinstellungen, fehlen aber im neuen Cockpit. Dadurch müssen Nutzer für zentrale Projektinformationen den Arbeitskontext verlassen.

## Wie

- Drei Buttons in der Cockpit-Topbar öffnen jeweils ein fokussiertes Overlay.
- Die bestehenden Komponenten `StatsTab`, `SessionsTab` und `AuditTab` sowie ihre bestehenden APIs werden wiederverwendet.
- Overlays sind projektgebunden und zeigen den Projektnamen.
- Es entstehen keine automatischen Datamining-Abfragen und keine neuen Backend-Endpunkte.

## Implementierungsreihenfolge

1. Wiederverwendbares Cockpit-Insights-Overlay für die drei Ansichten anlegen.
2. Zustände und Topbar-Aktionen im Project-Cockpit ergänzen.
3. Frontend-Build und Offline-first-Guard ausführen.
4. Architektur-Review durchführen und Änderungen committen.

## Akzeptanzkriterien

- Statistiken, Sessions und Audit sind für ein aktives Projekt direkt im Cockpit erreichbar.
- Die Statistikwerte stammen aus der bestehenden Projekt-Stats-API.
- Jede gelistete Session kann in der Werkstatt geöffnet werden.
- Audit kann nach Aktion und Benutzer gefiltert werden.
- Ohne aktives Projekt sind die Aktionen deaktiviert.
- Es gibt keine zusätzliche Datamining-Abfrage.
- Frontend-Build und Cockpit-Offline-Guard sind grün.

## Nicht enthalten

- Neue Statistikmetriken oder Diagramme.
- Änderungen an Audit-Aufbewahrung oder Audit-Aktionstypen.
- Session-Suche, Pagination oder Datamining-Auswertung.
- Neue Backend-Endpunkte oder Datenbankmigrationen.
