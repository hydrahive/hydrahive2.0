# Project-Cockpit P7: Sichere Projektintegrationen

## Was

Das Project-Cockpit erhält ein Integrations-Overlay für projektbezogene MCP-Server, erlaubte Plugins, einen optionalen LLM-API-Key und Samba-Freigaben.

## Warum

Diese Einstellungen sind bislang nur in der alten Projektverwaltung erreichbar. Die bestehende Oberfläche vermischt sie mit Status und Projektlöschung und kann Samba-Passwörter im Klartext anzeigen oder kopieren. Das Cockpit benötigt eine fokussierte, sichere Arbeitsfläche.

## Wie

- Ein Topbar-Button **Integrationen** öffnet das projektgebundene Overlay.
- MCP-Server-IDs und Plugins verwenden die bestehende Projekt-Update-API.
- Ein bestehender API-Key wird nie in ein Eingabefeld übernommen. Das Feld dient nur zum Ersetzen oder expliziten Entfernen.
- Samba kann über die bestehende API aktiviert oder deaktiviert werden.
- Samba-Adresse und Benutzer dürfen angezeigt und kopiert werden; das Passwort wird im Cockpit weder ausgegeben noch kopiert.
- Projektstatus und Projektlöschung sind nicht Teil des Overlays.
- Butler/Webhooks bleiben ein separater Backend-Slice, da derzeit keine projektbezogene API existiert.

## Implementierungsreihenfolge

1. Sichere Integrations-Formkomponente erstellen.
2. Cockpit-Overlay und Aktion unter **Verwalten** ergänzen.
3. Aktualisierte Projektdaten in den Cockpit-State übernehmen.
4. Build, Offline-Guard, Diff- und Security-Prüfung ausführen.

## Akzeptanzkriterien

- MCP-Server und erlaubte Plugins können gespeichert werden.
- Bestehende LLM-API-Keys werden nicht angezeigt oder in den Clientzustand des Formulars kopiert.
- API-Key kann ersetzt und explizit entfernt werden.
- Samba kann aktiviert/deaktiviert werden.
- Samba-Passwort ist im Overlay weder sichtbar noch kopierbar.
- Keine doppelten Status- oder Löschfunktionen.
- Keine neuen Backend-Endpunkte.
- Frontend-Build und Cockpit-Offline-Guard sind grün.

## Nicht enthalten

- Butler- oder Webhook-Konfiguration.
- Neue MCP-, Plugin-, Samba- oder Secret-APIs.
- Klartextanzeige bestehender Secrets.
