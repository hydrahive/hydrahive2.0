# Plan: Gemeinsamer Reiter-Baustein + Archiv-Fenster mit Reitern

Task `36bd2884` („Lange Seiten kürzen“), Schritt 3, erster PR. Till hat die Aufteilung am 30.10.2026 freigegeben.
Messung (Konto hydratest, 1440×900): Das Archiv-Fenster ist **5,1 Bildschirme** lang.

## Ziel

1. **`AdminTabs`** (neu, `features/cockpit/admin/ui/AdminTabs.tsx`): ein Reiterbaustein für alle Admin-Fenster.
   - Der Reiter steht in der Adresse (`tab=`). Neuladen und Lesezeichen behalten ihn. Ein unbekannter oder fehlender Wert ergibt den ersten Reiter.
   - ARIA: `tablist`, `tab` mit `aria-selected`/`aria-controls`, `tabpanel`; Pfeiltasten ←/→ wechseln den Reiter.
   - Optionaler Zähler je Reiter (z. B. „Inhalt 12“) und optionaler **Punkt** für „hier ist etwas“
     (laufender Vorgang, Fehler). Regel `regel.seiten-kurz-halten`.
   - Auf schmalen Bildschirmen umbrechend (grid 2 Spalten), ab `sm` in einer Zeile.
   - Die Logik steckt in den reinen Funktionen `parseTab(list, value)` und `withTab(search, id)` in `adminTabs.ts`.
2. Das **Föderations-Fenster** nutzt den Baustein. Aussehen und Adresse (`tab=workstations` …) bleiben gleich.
3. Das **Archiv-Fenster** bekommt drei Reiter:
   - `speicher`: Speicherort, Netzwerk-Freigabe, Externer Server (NAS)
   - `vorgaenge`: Laufende Vorgänge, Waisen. Ein Punkt erscheint, wenn ein Vorgang läuft oder wartet bzw. Waisen gefunden sind.
   - `inhalt`: Archivierte Elemente (Zähler = Anzahl)
   - Fehler stehen über den Reitern, sind also in jedem Reiter sichtbar.

## Dateien

- `frontend/src/features/cockpit/admin/ui/adminTabs.ts` + `adminTabs.test.ts` (neu)
- `frontend/src/features/cockpit/admin/ui/AdminTabs.tsx` + `AdminTabs.test.tsx` (neu), Export in `ui/index.ts`
- `frontend/src/features/cockpit/admin/FederationOverlay.tsx`: auf `AdminTabs`
- `frontend/src/features/archive/archiveTabs.ts` + Test (neu): Reiterliste, Punkt-/Zählerregeln
- `frontend/src/features/archive/ArchiveView.tsx`: neue Eigenschaft `tab`, zeigt nur die Bereiche des Reiters
- `frontend/src/features/archive/ArchiveOverlay.tsx`: Reiter aus der Adresse, `AdminTabs` über `ArchiveView`
- `frontend/src/features/archive/ArchiveView.test.tsx`: Test „fünf Bereiche“ wird je Reiter geprüft
- i18n `archive.json` de/en: `tabs.speicher|vorgaenge|inhalt`

## Implementierungsreihenfolge

### Task 1: Reiter-Logik
- [ ] `adminTabs.test.ts` (ROT):
  - `parseTab(["a","b"], "b")` ergibt `"b"`, `null`/unbekannt ergibt `"a"`
  - `withTab("?section=archive", "b")` ergibt `"?section=archive&tab=b"`, ein vorhandenes `tab` wird ersetzt, andere Werte bleiben
- [ ] Umsetzen (GRÜN), Mutante: Rückfall auf den letzten statt auf den ersten Reiter

### Task 2: Baustein `AdminTabs`
- [ ] `AdminTabs.test.tsx` (ROT):
  - Rollen, `aria-selected` nur am aktiven Reiter
  - Zähler wird gezeigt, Punkt mit Bildschirmleser-Text
  - `onKeyDown` →/← liefert den nächsten bzw. vorigen Reiter, am Ende wieder vorn (reine Funktion `nextTab`)
- [ ] Umsetzen, Föderation umstellen. `federationTabs.test.ts` bleibt grün.

### Task 3: Archiv-Reiter
- [ ] `archiveTabs.test.ts` (ROT):
  - Reihenfolge `speicher, vorgaenge, inhalt`, Rückfall `speicher`
  - Punkt bei `vorgaenge`, wenn `jobs.running`, `jobs.queued.length` oder `move.running` vorliegt oder wenn Waisen > 0 sind
  - Zähler `inhalt` = Anzahl der Einträge
- [ ] `ArchiveView.test.tsx` anpassen (ROT):
  - `tab="speicher"` → `storage, share[, remote]`
  - `tab="vorgaenge"` → `jobs, orphans`
  - `tab="inhalt"` → `entries`
  - Fehlertext in jedem Reiter
- [ ] Umsetzen (GRÜN), Mutanten: falscher Bereich im Reiter, Punkt fehlt bei wartendem Auftrag

### Task 4: Prüfung
- [ ] vitest voll, tsc, eslint, `npm run build`
- [ ] Browser mit Konto hydratest: Archiv bei 1440 px und 390 px, jeder Reiter höchstens etwa 1,5 Bildschirme; Neuladen behält den Reiter; Föderation unverändert
- [ ] Testserver für Till, danach PR

## Akzeptanzkriterien
- [ ] Archiv-Fenster: kein Reiter länger als etwa 1,5 Bildschirme (gemessen)
- [ ] Reiter steht in der Adresse, Neuladen behält ihn
- [ ] Föderation sieht aus wie vorher und verhält sich gleich
- [ ] Laufender Vorgang ist auch aus einem anderen Reiter heraus am Punkt zu erkennen

## Nicht in diesem Plan
- Module, System, Globale Einstellungen, Benutzer (je eigener PR mit `AdminTabs`)
- Dashboard (bewusst nicht, Till 30.10.)
- Umleitung der alten Seite `/federation` (eigener kleiner PR)
