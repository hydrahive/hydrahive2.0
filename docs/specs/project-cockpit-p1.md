# Plan: Project-Cockpit P1 – Basisdaten, Notizen und Löschen

## Ziel

Das aktive Projekt kann direkt im Cockpit bearbeitet werden. Name, Beschreibung, Status und Notizen werden explizit gespeichert; Löschen verlangt die exakte Eingabe des Projektnamens.

## Dateien

- `frontend/src/features/cockpit/project/ProjectDetailsOverlay.tsx` – Formular, Dirty-State, Fehler und Delete-Gate.
- `frontend/src/features/cockpit/ProjectCockpitPage.tsx` – sichtbarer Einstieg und lokales Aktualisieren/Entfernen.

## Implementierungsreihenfolge

1. Bestehende `projectsApi.update/delete` und Project-Typen wiederverwenden.
2. Nicht versehentlich schließbares Overlay erstellen.
3. Aktualisiertes Projekt in der Cockpit-Liste ersetzen.
4. Nach Delete Projektliste und aktive serverseitige Preference sauber aktualisieren.
5. Build und Offline-Guard prüfen.

## Akzeptanzkriterien

- Name, Beschreibung, Status und Notizen sind editier- und speicherbar.
- Unveränderte Form kann nicht gespeichert werden.
- Fehler bleiben im Overlay sichtbar.
- Löschen ist erst möglich, wenn der exakte Projektname eingegeben wurde.
- Outside-Click und Escape schließen das Overlay nicht.
