# Media-Cockpit: eindeutige Arbeitsbereiche

## Ziel

Die linke Navigation öffnet für jeden Produktionsbereich eine fachlich passende, bereits persistente Arbeitsfläche statt mehrere Einträge pauschal auf das Atelier zu verweisen.

## Verhalten

- **Idee** öffnet den Media-Projekt-Steckbrief und bearbeitet Name und Grundidee/Beschreibung.
- **Prompts** öffnet das persistente Promptarchiv.
- **Drehbuch & Regie** öffnet den Akt-/Szene-/Shot-Editor.
- **Charaktere** öffnet die Charakteransicht der Asset-Bibliothek.
- **Stil / CI** öffnet die Stilansicht der Asset-Bibliothek.
- **Assets** öffnet die gesamte Asset-Bibliothek.
- **Schnitt** öffnet die persistente Timeline.
- Das Atelier bleibt eine separate Erstellungsanwendung und ist kein pauschales Navigationsziel.

## Dateien

- `MediaCockpitPage.tsx` — Aktionen verdrahten und ausgewählten Media-Projektzustand aktualisieren.
- `MediaIdeaOverlay.tsx` — Projektname und Grundidee persistent bearbeiten.
- `mediaWorkspaceNavigation.ts` — zentrale Definition der Bereiche.

## Akzeptanzkriterien

- Kein linker Bereich verweist pauschal auf `/atelier`.
- Jeder Klick öffnet unmittelbar die benannte Arbeitsfläche.
- Idee, Prompt und Regie sind getrennte Funktionen.
- Drehbuch und Regie erscheinen als ein gemeinsamer Bereich.
- Speichern der Idee nutzt die bestehende Media-Projekt-API.
- Kein Klick startet Generierung oder LLM-Jobs.
