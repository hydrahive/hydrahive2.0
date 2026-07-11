# Media-Atelier Layout-Mock

## Was

Die funktionierende Atelier-Seite erhält ausschließlich ein neues Cockpit-Layout. Die vorhandenen Atelier-Komponenten und Abläufe bleiben unverändert.

## Warum

Der Produktionsablauf soll links auf einen Blick verständlich sein. Rechts steht jeweils eine große, ruhige Arbeitsfläche zur Verfügung. Das Layout bildet die visuelle Basis für den späteren Ausbau des Media-Cockpits.

## Layout

- Oben: bestehende neue `CockpitTopbar`, aktiver Bereich `media`.
- Links: Projektwahl und fünf vertikale Produktionsschritte.
- Rechts: ein Hauptfenster, dessen Inhalt mit dem gewählten Schritt wechselt.
- Schritte:
  1. Charaktere
  2. Bild erzeugen
  3. Galerie
  4. Videoclips
  5. Film erstellen
- Der alte Atelier-Header und die horizontalen Tabs entfallen.

## Verhalten

Der Mock ist rein visuell im Sinne des Umbaus: keine neuen APIs, Generatoren, Datenmodelle oder Produktionsfunktionen. Bereits bestehende Funktionen bleiben in den jeweiligen Schritten benutzbar. Bestehende automatische Übergänge Bild → Galerie und Video → Videoclips bleiben erhalten.

## Akzeptanzkriterien

- `/media` verwendet das Design der neuen Cockpit-Seiten.
- Die neue Cockpit-Topbar ist sichtbar.
- Der alte Atelier-Header ist entfernt.
- Alle fünf Produktionsschritte stehen links untereinander.
- Rechts ist immer genau eine bestehende Atelier-Arbeitsfläche sichtbar.
- Backend und Atelier-API bleiben unverändert.
- Frontend-Build und Cockpit-Guard sind grün.
