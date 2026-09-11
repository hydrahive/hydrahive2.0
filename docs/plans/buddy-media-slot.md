# Plan: Buddy-Media-Slot (Phase B)

## Ziel

Der vorhandene optionale Musicplayer erscheint wieder als echtes Widget in der rechten Buddy-Spalte. Die Einbindung nutzt einen expliziten, typisierten Media-Widget-Vertrag statt harter Modulimporte, Namensheuristiken oder der pauschalen Rückkehr aller Modulwidgets.

## Dateien

- `frontend/src/modules/types.ts` — öffentlicher typisierter Media-Widget-Vertrag für installierbare Module.
- `frontend/src/features/buddy/moduleMediaWidgets.ts` — Laufzeitvalidierung und deterministische Sortierung.
- `frontend/src/features/buddy/BuddyPage.tsx` — gültige Media-Widgets im rechten Buddy-Rail rendern.
- `frontend/scripts/gen-modules.mjs` — optionale `buddyMediaWidgets` einsammeln.
- `frontend/src/modules/index.generated.ts` — ignoriertes Build-Artefakt, vom Generator lokal aktualisiert.
- `core/tests/test_buddy_media_widget_contract.py` — Generator-/Buddy-Vertrag gegen Regressionen sichern.
- `hydrahive2-modules/musicplayer/frontend/index.tsx` — kanonische Hub-Quelle registriert den Musicplayer.
- `hydrahive2-modules/musicplayer/tests/test_frontend_contract.py` — Hub-Regressionsprüfung.
- `hydrahive2-modules/README.md` und `README.de.md` — neuen Modulvertrag dokumentieren.

## Implementierungsreihenfolge

### Task 1: Contract-Tests (RED)

- [x] Core-Test verlangt Generator-Export `moduleBuddyMediaWidgets`, Laufzeitnormalisierung und Buddy-Konsum.
- [x] Musicplayer-Test verlangt stabilen `buddyMediaWidgets`-Deskriptor.
- [x] Tests ausführen und erwartetes Rot dokumentieren.

### Task 2: Typisierter optionaler Media-Widget-Vertrag (GREEN)

- [x] `BuddyMediaWidget` und `BuddyMediaWidgetProps` definieren.
- [x] Unbekannte Generatorwerte per Type Guard validieren.
- [x] Doppelte IDs deterministisch nur einmal übernehmen.
- [x] Nach `order`, dann `id` sortieren.
- [x] `gen-modules.mjs` um den optionalen Export erweitern und Generated File neu erzeugen.
- [x] Musicplayer mit stabiler ID und Reihenfolge registrieren.
- [x] Contract-Tests grün ausführen.

### Task 3: Buddy-Integration

- [x] `BuddyPage` konsumiert ausschließlich `moduleBuddyMediaWidgets`.
- [x] Media-Widgets direkt oberhalb des kompakten Werkzeug-Panels rendern.
- [x] `onPrompt` und aktuelle `projectId` weiterreichen.
- [x] Musik-Link entfernen, wenn der echte eingebettete Player verfügbar ist; andere Links bleiben lokal/offline-first.
- [x] Core-Frontend ohne installierte Module bauen.
- [x] Core-Frontend mit installierten Modulen bauen.

### Task 4: Verifikation und Veröffentlichung

- [x] Musicplayer-Backendtests grün.
- [x] Core-Vertragstests grün.
- [x] TypeScript-Build, ESLint und Cockpit-Offline-Guard grün.
- [ ] Browser: Player sichtbar; zehn Tracks laden; Play/Pause, Seek und Lautstärke testen.
- [x] HydraHive-Strukturreview vor Commit.
- [ ] Core und Modul-Hub atomar committen und pushen.
- [ ] Installiertes Modul aktualisieren, Frontend bauen, Dienst neu starten und erneut smoken.

## Akzeptanzkriterien

- [ ] Installierter Musicplayer ist im Buddy wieder sichtbar und funktionsfähig.
- [ ] Musicplayer-Daten und zehn vorhandene Tracks bleiben unverändert.
- [ ] Deinstallierter Musicplayer verursacht weder Buildfehler noch leeren Media-Container.
- [ ] Allgemeine Buddy-Widgets erscheinen nicht versehentlich im Media-Slot.
- [ ] Der neue Vertrag ist in Core und Modul-Hub konsistent dokumentiert.

## Nicht in diesem Plan

- Video-Support und eigener Player-Tab (Phase C).
- Globale, seitenübergreifende Wiedergabe (Entscheidung vor Phase C).
- Backend-/Migrations-/Stream-Auth-Änderungen.
- Allgemeine Wiederherstellung aller früheren Buddy-Widgets.
