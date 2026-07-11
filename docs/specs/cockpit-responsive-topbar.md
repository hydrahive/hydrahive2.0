# Cockpit-Chrome P1: Responsive Topbar und Mobile-Navigation

## Was

Die zentrale Cockpit-Topbar wird mehrstufig responsiv. Große Displays zeigen Navigation und Aktionen direkt, mittlere Displays bündeln Seitenaktionen in einem Menü und kleine Displays verwenden einen mobilen Drawer.

## Warum

Die aktuelle starre Zeile läuft besonders im Project-Cockpit mit vielen Aktionen über. Navigation und wichtige Funktionen werden dadurch auf Notebook- und Mobilbreiten unerreichbar.

## Wie

- Ab großen Displays bleiben Cockpit-Navigation, Kontext und Seitenaktionen sichtbar.
- Auf mittleren Displays bleiben Logo und Cockpit-Navigation sichtbar; Seitenaktionen, Kontext, Seitensprung und Profil liegen im Menü **Aktionen**.
- Auf kleinen Displays bleiben Logo, aktiver Bereich und ein Menübutton sichtbar; Navigation und Aktionen erscheinen in einem rechten Drawer.
- Escape und ein Klick auf den Hintergrund schließen offene Menüs.
- Beim Öffnen erhält der erste Menüpunkt Fokus; beim Schließen kehrt der Fokus zum Auslöser zurück.
- Navigation und vorhandene Aktionen behalten ihre bisherigen Ziele und Handler.

## Implementierungsreihenfolge

1. Desktop-, Tablet- und Mobile-Darstellung in `CockpitTopbar` strukturieren.
2. Tastatur- und Fokusverhalten ergänzen.
3. Build und Offline-Guard ausführen.
4. Architektur- und Diff-Prüfung durchführen.

## Akzeptanzkriterien

- Kein horizontaler Überlauf der Topbar bei kleinen oder mittleren Viewports.
- Alle Cockpit-Sparten bleiben auf jeder Breite erreichbar.
- Alle `extraActions`, die optionale Seitenaktion und Profil bleiben erreichbar.
- Escape und Hintergrundklick schließen offene Menüs.
- Menübuttons besitzen `aria-expanded` und `aria-controls`.
- Fokus wird beim Öffnen und Schließen nachvollziehbar geführt.
- Frontend-Build und Cockpit-Offline-Guard sind grün.

## Nicht enthalten

- Apps-/Bento-Menü, echtes Avatar-/Logout-Menü oder kontextuelle Hilfe; diese folgen in Cockpit-Chrome P2.
- Änderungen an den einzelnen Cockpit-Inhalten.
