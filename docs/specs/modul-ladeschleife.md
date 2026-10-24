# Modul-Listen erst beim Gebrauch lesen (Werkstatt schwarz)

Task 08c5c546. Meldung von Till am 24.10.2026: Nach dem Update (Kern `afd1deae`, 29 Modul-Updates) bleibt die
Werkstatt komplett schwarz.

## Ursache (nachgestellt auf hydratest)

Fehler bei 1600 px: `Cannot read properties of undefined (reading 'map')` in `WorkspacePanel`.

Die Lade-Schleife beim Start:
- `modules/index.generated.ts` importiert alle Module, darunter `legal`.
- `legal` lädt `LegalPage` → `CaseFile` → `CaseChat` → `@/features/chat/ChatPane` →
  `./workspace/WorkspacePanel`.
- `WorkspacePanel` liest auf oberster Ebene `const extraTabs = moduleWorkspaceTabs`. Zu diesem Zeitpunkt lädt
  `index.generated` gerade `legal`, deshalb ist der Wert noch `undefined`.
- Beim Anzeigen der rechten Werkstatt-Leiste (am Handy zugeklappt) wirft `extraTabs.map`.

Das ist nicht durch #618, #619 oder #261 verursacht. Mit Kern 7e7a59f7 und Modulen von heute ist die Werkstatt
genauso schwarz, ohne `legal` ist sie in Ordnung. Eingeführt hat es legal 0.2.0 (20.10., Fall-Chat).

## Lösung

Dasselbe Muster wie `nav-config.ts` (`moduleNavItems()`): Modul-Listen aus `index.generated` **nie** auf oberster
Ebene in eine Konstante kopieren, sondern **erst beim Gebrauch** lesen, also in einer Funktion. Zur Laufzeit ist
der Wert gesetzt (ES-Module-Live-Binding).

Betroffene Stellen:

| Datei | heute | neu |
|---|---|---|
| `features/chat/workspace/WorkspacePanel.tsx` | `const extraTabs = moduleWorkspaceTabs` | `workspaceTabs()` im Rendern |
| `features/cockpit/media/mediaRegistry.ts` | `export const mediaSources/mediaWorkflows` | `mediaSources()` / `mediaWorkflows()` |
| `features/buddy/BuddyPage.tsx` | `const BUDDY_MEDIA_WIDGETS = …` | Funktion im Rendern |
| `features/themetemplates/registry.tsx` | `SLOT_BLOCKS = [..., ...moduleSlotBlocks]` | Kern-Bausteine konstant, `slotBlocks()` fügt Modul-Bausteine beim Aufruf an |

Gemeinsamer Helfer `shared/moduleList.ts`: `moduleList<T>(value)` gibt `[]` zurück, wenn der Wert (noch) kein Array
ist. So stürzt auch ein künftiger Zyklus nicht ab, sondern zeigt die Modul-Teile im schlimmsten Fall nicht an.

`App.tsx` (`moduleRoutes`) und `i18n/index.ts` (`moduleI18n`) bleiben. Beide werden nur aus `main.tsx` geladen,
nachdem `index.generated` vollständig ausgewertet ist, und kein Modul importiert sie.

**Wächter-Test** `shared/moduleListGuard.test.ts`: Er liest alle Kern-Dateien, die aus `@/modules/index.generated`
importieren, und schlägt fehl, wenn dort ein `module…`-Wert auf oberster Ebene in eine Konstante übernommen wird.
Erlaubt sind nur `App.tsx` und `i18n/index.ts`.

## Akzeptanzkriterien

- Rote Tests vorher:
  - `WorkspacePanel` zeigt mit `moduleWorkspaceTabs === undefined` beim Laden und einem Tab beim Rendern
    beides an. Den Schleifen-Zustand stellt ein Test nach, der den Wert erst nach dem Import setzt.
  - `mediaWorkflows()` und `slotBlocks()` sehen später gesetzte Modul-Werte.
  - `moduleList` gibt `[]` für `undefined` zurück.
  - Der Wächter-Test findet die heutigen Stellen.
- hydratest mit allen Modulen: `/werkstatt` bei 1600 px ohne Seitenfehler, Dateien-/Git-/Tasks-Reiter sichtbar.
  Buddy, Media, Atelier und Startseite weiter ohne Fehler.
- Volle Testreihe, `tsc -b`, eslint ohne neue Befunde, Mutanten.

## Nicht enthalten

- Das Recht-Modul selbst ändern. Es darf den Kern-Chat benutzen, der Kern muss das aushalten.
