# Media-Trailer-Workflow Recovery

## Ziel

Die Route `/media` stellt sofort wieder den bewährten, zusammenhängenden Atelier-Ablauf bereit: Charaktere wählen, Bild erzeugen, Bild ansehen, daraus Video erzeugen, Clips abspielen, Clips auswählen, Film rendern und Film abspielen.

## Entscheidung

Das unverbundene Media-Cockpit wird nicht weiter repariert oder neu gestaltet. `/media` verwendet vorläufig direkt den bestehenden `AtelierPage`-Workflow. Dessen Backend und Dateien bleiben unverändert. Die neueren Media-Projekt-, Prompt-, Regie- und Timeline-Daten werden nicht gelöscht; sie sind lediglich nicht Teil des primären Trailer-Ablaufs.

## Ablauf

1. Projekt auswählen.
2. Charaktere links auswählen oder verwalten.
3. Im Tab **Generieren** ein Bild erzeugen.
4. Automatisch in die **Galerie** wechseln, Bild vergrößern und über 🎬 ein Video starten.
5. Automatisch zu **Videos** wechseln und fertige Clips direkt abspielen.
6. Rechts Clips in gewünschter Reihenfolge auswählen und Film rendern.
7. Fertigen Film direkt im Player abspielen.

## Dateien

- `frontend/src/features/cockpit/MediaCockpitPage.tsx` — schlanker Recovery-Einstieg, der die bewährte Atelier-Arbeitsfläche rendert.
- `frontend/src/modules/atelier/*` — bestehender funktionierender Workflow, unverändert.

## Akzeptanzkriterien

- `/media` zeigt keine unverbundenen Idee-/Prompt-/Regie-Overlays mehr.
- Bilder können vergrößert werden.
- Bilder können unmittelbar als Videostartbild verwendet werden.
- Fertige Videos und Filme haben sichtbare Player.
- Fertige Clips können in Reihenfolge ausgewählt und zu einem Film gerendert werden.
- Bestehende Media-Projektdaten werden nicht gelöscht oder migriert.

## Nicht enthalten

- Neues UX-Design.
- Änderungen an Generator- oder Film-APIs.
- Löschung der neueren Media-Workspace-Komponenten.
- Umbau des Atelier-Workflows.
