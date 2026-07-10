# Plan: Buddy-Widget-Effekte

## Ziel
Die rechte Buddy-Spalte darf keine Fake-Buttons enthalten. Musik, Games, Scratchpad/Wühlkiste und Modulwidgets sollen entweder sofort eine echte vorhandene Aktion ausführen oder klar als geplanter Integrationspunkt markiert sein.

## Ist-Problem
- Die globale Layout-Topbar wurde auf `/buddy` noch zusätzlich gerendert, weil `/buddy` nicht als Cockpit-Route behandelt wurde.
- Der Buddy-Extensions-/Anwendungen-Blob erzeugt visuelle Altlasten und gehört nicht in das neue Buddy-Mockup.
- Die vier Mini-Kacheln Musik/Games/Wühlkiste/Scratchpad senden Slash-Kommandos, die keine garantierte UI-Aktion auslösen. Das wirkt kaputt.

## Implementierungsreihenfolge

### Task 1: Chrome bereinigen
- [x] `/buddy` in die Cockpit-Routen des globalen Layouts aufnehmen.
- [x] `BuddyExtensionsPanel` aus dem neuen Buddy-Cockpit entfernen.
- [x] Keine doppelte/alte Topnav und kein Anwendungen-Bento auf Buddy.

### Task 2: Fake-Kacheln entfernen
- [x] Mini-Kacheln nicht mehr als Pseudo-Aktionsbuttons rendern.
- [x] Rechte Spalte zeigt stattdessen einen Plan-/Statusblock und die echten Modulwidgets.

### Task 3: Echte Widget-Effekte als nächste Umsetzung
- [ ] Musik: vorhandenes `MusicPlayerBuddyBox` als primäre Musikfläche, später Play/Pause/Upload als direkte UI-Controls extrahieren.
- [ ] Games: vorhandene Minigames/Boardgames-BuddyWidgets direkt als Kacheln nutzen; Quicklinks nur zu `/minigames` und `/boardgames`.
- [ ] Scratchpad/Wühlkiste: echte Scratchpad-API-Aktion definieren (Notiz anlegen/öffnen) statt Slash-Command-Placeholder.
- [ ] Widget-Sichtbarkeit serverseitig über Buddy-Cockpit-Prefs speichern.

## Akzeptanzkriterien
- [x] Buddy hat nur noch die CockpitTopbar, nicht zusätzlich das alte globale Menü.
- [x] Anwendungen/Extensions-Blob ist weg.
- [x] Keine rechte Kachel behauptet eine direkte Aktion, wenn sie noch keine echte Aktion hat.
- [ ] Follow-up: echte Widget-Aktionen implementiert und getestet.

## Nicht in diesem Fix
- Keine neuen Backend-Endpunkte für Scratchpad/Wühlkiste.
- Keine direkte MusicPlayer-Control-Extraktion.
- Keine Widget-Prefs-Migration.
