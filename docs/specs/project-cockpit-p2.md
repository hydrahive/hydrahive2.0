# Plan: Project-Cockpit P2 – Mitglieder und Spezialisten

## Ziel

Mitglieder und freigegebene Spezialisten des aktiven Projekts sind direkt im Cockpit verwaltbar. Bestehende APIs und bewährte Komponenten werden wiederverwendet; Änderungen aktualisieren sofort den Cockpit-Zustand.

## Umsetzung

- Gemeinsames, explizit schließbares Verwaltungs-Overlay.
- `MemberManager` für verfügbare User sowie Add/Remove-API.
- `SpecialistsTab` für AgentLink-Status, Spezialistenliste und `allowed_specialists`.
- Sichtbarer Einstieg in der Project-Cockpit-Topbar.

## Akzeptanzkriterien

- Mitglieder können hinzugefügt und nach Bestätigung entfernt werden.
- Spezialisten können ausgewählt und explizit gespeichert werden.
- Änderungen erscheinen ohne Reload im aktiven Projekt.
- Lade-/Fehlerzustände der bestehenden Komponenten bleiben erhalten.
- Outside-Click und Escape schließen das Overlay nicht.
