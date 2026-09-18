# Legacy-Topnav auf Cockpit-Standard angleichen

## Was

Das Standard-Theme (`TopnavLayout`) erhält dieselbe globale Topbar-Formensprache wie die bereits migrierten Cockpit-Seiten: kompakte dunkle Navy-Fläche, einheitliche Ränder, Fokuszustände und responsive Bedienbarkeit.

## Warum

Aktuell existieren zwei deutlich sichtbare Topbar-Standards: `CockpitTopbar` für die neuen Cockpits und eine ältere Topnav für alle übrigen Routen. Die erste Migrationsetappe soll die globale Oberfläche angleichen, ohne Legacy-Seiten, Routing oder Funktionen zu migrieren.

## Wie

- `TopnavLayout` bleibt das Layout-Gerüst und behält `quickLinks`, Einstellungen, Apps/Bento, Avatar-Menü und Footer-Update bei.
- Nur die visuelle Topbar-Struktur und ihre Zustände werden auf die Cockpit-Formensprache umgestellt.
- Inhalt, Route-Ziele und Theme-Verträge bleiben unverändert.
- `SidebarLayout` sowie benutzerdefinierte Themes sind nicht Teil dieser Etappe.

## Akzeptanzkriterien

- Standard-Legacy-Routen zeigen eine Topbar im Cockpit-Farbschema.
- Aktive, Hover- und Fokuszustände bleiben sichtbar und kontrastreich.
- Logo, Quicklinks, Einstellungen, Apps/Bento und Benutzermenü bleiben erreichbar.
- Mobile Navigation bleibt ohne horizontalen Überlauf nutzbar.
- TypeScript-Build und bestehende Frontend-Checks bleiben grün.
