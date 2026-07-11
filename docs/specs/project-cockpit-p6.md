# Project-Cockpit P6: Git- und Gitea-Detailverwaltung

## Was

Das Project-Cockpit erhält eine vollständige Git-Verwaltung als fokussiertes Overlay. Darin sind die bereits vorhandenen Funktionen für Init, Clone, Repository-Details, Commit, Remote-Konfiguration, Pull, Push, Initial Push und kontrolliertes Entfernen erreichbar.

## Warum

Die kompakte Git-Zusammenfassung im Cockpit eignet sich für den schnellen Status, bietet aber nicht alle bestehenden Verwaltungsaktionen. Nutzer sollen dafür den Projektkontext nicht verlassen müssen.

## Wie

- Ein Button **Git verwalten** in der Cockpit-Topbar öffnet ein projektgebundenes Overlay.
- Das Overlay verwendet den bestehenden `GitTab` und damit dieselben APIs und Sicherheitsprüfungen wie die Projekteinstellungen.
- Nach Änderungen wird die kompakte Git-Zusammenfassung durch erneutes Einhängen aktualisiert.
- Zugangstokens werden nicht aus gespeicherten Daten geladen oder im Overlay ausgegeben. Ein beim Clone eingegebenes Token bleibt ein maskiertes Eingabefeld und wird nur für den Request verwendet.
- Es entstehen keine neuen Backend-Endpunkte.

## Implementierungsreihenfolge

1. Git-Verwaltungs-Overlay mit bestehendem `GitTab` anlegen.
2. Topbar-Aktion und Overlay-Zustand im Project-Cockpit ergänzen.
3. Git-Zusammenfassung nach Verwaltungsänderungen aktualisieren.
4. Build, Offline-Guard, Diff- und Security-Prüfung ausführen.

## Akzeptanzkriterien

- Vollständige bestehende Git-Verwaltung ist direkt im Cockpit erreichbar.
- Ohne aktives Projekt ist die Aktion deaktiviert.
- Die kompakte Git-Zusammenfassung bleibt bestehen und aktualisiert sich nach Änderungen.
- Entfernen verlangt weiterhin eine ausdrückliche Bestätigung.
- Gespeicherte Tokens werden nicht angezeigt.
- Es gibt keine neuen Backend-Endpunkte oder Git-Ausführungspfade.
- Frontend-Build und Cockpit-Offline-Guard sind grün.

## Nicht enthalten

- Neue Git-Operationen oder Gitea-Endpunkte.
- Darstellung gespeicherter Credentials oder Tokens.
- Automatische Pushes, Pulls oder Repository-Löschungen.
