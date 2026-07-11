# Plan: Project-Cockpit P3 – Server, VMs und Container

## Ziel

Die bestehende projektgebundene Serververwaltung ist direkt aus dem Cockpit erreichbar, ohne ihre Sicherheitsbestätigungen oder Detailnavigation zu verlieren.

## Umsetzung

- `ServersTab`, `ServerRow` und `AddServerForm` unverändert wiederverwenden.
- Explizit schließbares Overlay über **Verwalten → Server** im linken Projektpanel.
- Zuweisung nutzt ausschließlich vorhandene serverseitig gefilterte Available-API.
- Entfernen bleibt durch vorhandenen Bestätigungsdialog geschützt.

## Akzeptanzkriterien

- Zugeordnete VMs/Container mit Zustand, CPU, RAM, Disk/Image werden angezeigt.
- Verfügbare Server können zugewiesen werden.
- Entfernen verlangt Bestätigung.
- Detailseiten bleiben erreichbar.
- Lade- und API-Fehler sind sichtbar.
