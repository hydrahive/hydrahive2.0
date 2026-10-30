# Plan: Module-Fenster mit Reitern und Suche

Task `36bd2884`, Schritt 3, zweiter PR (nach #659 `AdminTabs`). Till hat die Aufteilung am 30.10.2026 freigegeben:
„Module: Reiter Installiert / Verfügbar, Suchfeld, Updates oben“.
Messung (Konto hydratest, 1440×900): **4,5 Bildschirme**, 33 Module, 23 davon installiert, alle untereinander.

## Ziel

- Zwei Reiter über `AdminTabs`, Adresse `tab=installiert|verfuegbar`:
  - **Installiert** (Zähler). Punkt, wenn ein installiertes Modul ein Update hat oder nicht geladen ist.
  - **Verfügbar** (Zähler)
- **Suchfeld** über den Reitern. Es filtert Name, Kennung und Beschreibung; Groß-/Kleinschreibung zählt nicht, Leerzeichen am Rand werden ignoriert.
  Die Zähler zeigen die Treffer.
- **Reihenfolge:** zuerst Fehler (installiert, nicht geladen), dann Update verfügbar, dann nach Name.
- **Kein Verschwinden mitten im Ablauf:** Wer im Reiter „Verfügbar“ installiert, sähe das Modul nach dem Neuladen
  sonst im anderen Reiter, und Protokoll und Erfolgsmeldung wären weg. Module mit einer Aktion in dieser Sitzung bleiben deshalb im
  aktuellen Reiter (gilt bis zum Schließen des Fensters).
- Der Knopf „Installieren“ nutzt die Cockpit-Primärfarbe statt `bg-violet-600` (Spec verbietet Violett im Admin-Baum).

## Dateien

- `frontend/src/features/cockpit/admin/moduleTabs.ts` + `moduleTabs.test.ts` (neu): `MODULE_TABS`, `parseModuleTab`,
  `moduleView(modules, tab, query, pinned)`, `moduleTabs(modules, query, t)`
- `frontend/src/features/cockpit/admin/ModulesOverlay.tsx`: Suchfeld, `AdminTabs`, Liste aus `moduleView`
- `frontend/src/features/cockpit/admin/ModuleCockpitCard.tsx`: optional `onAction(id)`, Installieren-Knopf in Primärfarbe
- i18n `modules.json` de/en: `tabs.installiert|verfuegbar`, `search.placeholder`, `search.none`

## Implementierungsreihenfolge

### Task 1: Logik (`moduleTabs.ts`)
- [ ] Tests (ROT):
  - Reiter `installiert, verfuegbar`, Rückfall `installiert`
  - Filter nach Reiter. Suche „MAIL“ findet über den Namen, über die Kennung, über die Beschreibung; „ mail “ trimmt
  - Reihenfolge: Fehler vor Update vor Rest, innerhalb nach Name (`localeCompare` de)
  - angeheftete Kennung bleibt im Reiter, obwohl der Status gewechselt hat
  - Zähler = Treffer je Reiter, Punkt nur bei `installiert` mit Update oder Fehler
- [ ] Umsetzen (GRÜN), Mutanten: Fehler nicht nach oben, Beschreibung nicht durchsucht, Anheften wirkungslos

### Task 2: Fenster
- [ ] Umsetzen. Leere Trefferliste: Hinweis „Kein Modul passt zur Suche.“
- [ ] Bestehende Tests (`updateAllButton.test.tsx`) bleiben grün

### Task 3: Prüfung
- [ ] vitest, tsc, eslint, build
- [ ] Browser hydratest 1440/390: jeder Reiter gemessen, Suche, Neuladen behält den Reiter
- [ ] Testserver für Till, danach PR

## Akzeptanz
- [ ] Reiter „Installiert“ deutlich kürzer als 4,5 Bildschirme, „Verfügbar“ höchstens etwa 1,5
- [ ] Updates und Fehler stehen oben, der Punkt am Reiter zeigt sie auch aus „Verfügbar“
- [ ] Installieren aus „Verfügbar“: Protokoll bleibt sichtbar

## Nicht in diesem Plan
Alte Seite `/modules` (`ModulesPage`) – sie leitet nicht ins Admin-Fenster. Das prüfe ich gesondert bei der Umleitung `/federation`.
