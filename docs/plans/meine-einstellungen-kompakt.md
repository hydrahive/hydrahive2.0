# Plan: „Meine Einstellungen“ kompakt, Reiter statt Spalten

Task 36bd2884, Folgeschritt zu #634. Tills Befund (26.10.2026): „das rechts/links-Menü ist
too much, das Ganze müsste kompakter sein, eventuell im Tab-Container“. Er hat den Vorschlag
freigegeben: Reiter oben, Auswahlfeld mit Suche statt rechter Liste, Inhalt über volle Breite.

## Ziel

```
┌ Meine Einstellungen ────────────────────────────────────────────────┐
│ [Agenten] [Projekte] [Kommunikation] [Zugangsdaten] [Skills] [Butler] │  Reiter (URL /settings/:groupId)
├─────────────────────────────────────────────────────────────────────┤
│ Agent: [ 🔍 admin's Assistant · Master · claude-sonnet-4-6 ▾ ] [+ Neu] │  nur bei Agenten/Projekten
│ … Inhalt der Gruppe über die volle Breite …                         │
└─────────────────────────────────────────────────────────────────────┘
```

- Linke Gruppenspalte (`GroupList`) und rechte Liste (`AgentSubMenu`, `ProjectSubMenu`,
  `SubMenu`) entfallen.
- Gruppe = Reiter; die URL bleibt `/settings/:groupId` (Lesezeichen und Umleitungen aus
  #634 gelten weiter).
- Auswahl Agent/Projekt: Suchfeld mit aufklappender Trefferliste (Combobox). Die Auswahl
  steht in der URL (`?item=<id>`), damit Neuladen und Links den gewählten Agenten behalten.
  Ohne `item` wird der erste Eintrag vorgewählt (kein leerer „bitte wählen“-Zustand).
- Innere Reiterleiste (`ContentArea`: „Discord · WhatsApp · Mail“) bleibt nur, wo eine
  Gruppe wirklich mehrere Teile hat (Kommunikation). Einzelne Pseudo-Reiter wie
  „Credentials“, „Bibliothek“, „Flows“, „Einstellungen“ entfallen.
- Kein zusätzlicher Rahmen um eingebettete Seiten; Butler bekommt die volle Höhe
  (statt `EmbedFrame` mit eigenem Kasten).

## Dateien

- `frontend/src/features/settings/ItemPicker.tsx` (neu): Combobox (Suchfeld, Trefferliste,
  Tastatur ↑/↓/Enter/Escape, `role="combobox"`/`listbox`/`option`), Props:
  `items: PickerItem[]`, `value`, `onChange`, `label`, `onCreate?`
- `frontend/src/features/settings/pickerFilter.ts` (neu): `filterItems(items, query)`
  findet Treffer in Name und Zusatz (Typ, Modell), ohne Rücksicht auf Groß/Klein, Leerzeichen
  am Rand ignoriert
- `frontend/src/features/settings/pickerFilter.test.ts` (neu)
- `frontend/src/features/settings/ItemPicker.test.tsx` (neu): Darstellung (Label, Wert,
  ARIA, „+ Neu“ nur mit `onCreate`)
- `frontend/src/features/settings/detail/useAgentItems.ts`, `useProjectItems.ts` (neu):
  laden und sortieren wie bisher die Submenüs (Agent: Master → Projekt → Spezialist, dann
  Name; „off“ als Zusatz), liefern `PickerItem[]` + `reload`
- `frontend/src/features/settings/detail/itemsFrom.test.ts` (neu): Sortierung und
  Zusatztext (reine Funktionen `agentItems()`, `projectItems()` in `itemsFrom.ts`)
- `frontend/src/features/settings/detail/AgentSection.tsx`, `ProjectSection.tsx` (neu):
  Picker + „+ Neu“-Dialog + bestehende `AgentSettings`/`ProjectSettings` (diese bleiben,
  nur die Leer-Texte „Rechts … wählen“ ändern sich auf „Oben … wählen“)
- `frontend/src/features/settings/settingsTabs.ts` (neu): `selectedItem(search)` /
  `withItem(search, id)`, reine URL-Funktionen
- `frontend/src/features/settings/settingsTabs.test.ts` (neu)
- `frontend/src/features/settings/registry.ts`: `hasSubmenu`, `submenuLabel`,
  `submenuComponent`, `detailComponent` entfallen; Agenten/Projekte bekommen
  `component: AgentSection/ProjectSection`; `tabs` nur noch bei Kommunikation; Butler
  `fullHeight: true` statt `fullscreen`
- `frontend/src/features/settings/SettingsHubPage.tsx`: Kopf und Reiterleiste
  (`role="tablist"`, Stil wie Föderations-Fenster), darunter `ContentArea`
- `frontend/src/features/settings/ContentArea.tsx`: innere Reiter nur bei `tabs.length > 1`;
  kein Platzhalter-Zweig mehr (alle Gruppen haben Inhalt); Butler ohne EmbedFrame
- `frontend/src/features/settings/SettingsHubPage.test.tsx`: angepasst (Reiter statt Liste)
- entfernt: `GroupList.tsx`, `SubMenu.tsx`, `detail/AgentSubMenu.tsx`,
  `detail/ProjectSubMenu.tsx`, `EmbedFrame.tsx` (nach Prüfung: kein anderer Nutzer)

## Implementierungsreihenfolge

### Task 1: Suche und URL-Auswahl (reine Funktionen)
- [ ] `pickerFilter.test.ts`: leere Suche → alle; „SONNET“ findet über den Zusatz;
      „ admin “ trimmt; kein Treffer → `[]`; Reihenfolge bleibt
- [ ] `settingsTabs.test.ts`: `selectedItem("?item=a1")` → `"a1"`, ohne → `null`;
      `withItem("?x=1", "b2")` → `"?x=1&item=b2"`; `withItem("?item=a", null)` → `""`
- [ ] RED → Umsetzung → GREEN; Mutanten: `toLowerCase` entfernen, Zusatz nicht durchsuchen

### Task 2: Listen für Agenten und Projekte
- [ ] `itemsFrom.test.ts`: Agenten sortiert Master → Projekt → Spezialist → Name;
      Zusatz „Master · claude-sonnet-4-6“; deaktiviert → `dim: true`, Zusatz endet auf „· aus“;
      Projekte nach Name, `paused/archived` → `dim`
- [ ] RED → `itemsFrom.ts`, Hooks → GREEN; Mutante: Typ-Reihenfolge vertauschen

### Task 3: Auswahlfeld
- [ ] `ItemPicker.test.tsx`: Label sichtbar, `role="combobox"` mit
      `aria-expanded="false"`, Name des gewählten Eintrags im Feld; „+ Neu“ nur mit `onCreate`
- [ ] RED → `ItemPicker.tsx` → GREEN. Tastatur, Aufklappen und Suche werden auf der
      GUI-Reise im echten Browser geprüft (statisches Rendern kennt keine Eingaben)

### Task 4: Seite mit Reitern
- [ ] `SettingsHubPage.test.tsx`: sechs `role="tab"` in fester Reihenfolge; Reiter der
      URL-Gruppe `aria-selected="true"`; keine linke Gruppenliste (`Gruppe wählen` fehlt);
      Umleitungen aus #634 bleiben grün; Kommunikation zeigt innere Reiter, Zugangsdaten nicht
- [ ] RED → Registry, `SettingsHubPage`, `ContentArea`, Sections → GREEN
- [ ] Alte Dateien löschen; `tsc -b` zeigt, dass niemand sie mehr nutzt

### Task 5: Prüfen, GUI-Reise, PR
- [ ] tsc, eslint, vitest komplett, Build, Dateien ≤ 200 Zeilen
- [ ] Eigene Browser-Reise bei 1440 px und 390 px (Handy): jeder Reiter, Agent suchen
      („sonnet“), Tastatur ↓ Enter, Neuladen behält Agent, „+ Neu“ öffnet Dialog
      (abbrechen, nichts anlegen), Butler volle Höhe
- [ ] GUI-Reise mit Till → PR → CI → Merge

## Akzeptanzkriterien

- [ ] Keine Seiten- oder Rechtsspalte mehr; der Inhalt nutzt die volle Breite
- [ ] Agent/Projekt per Suche in wenigen Tasten auffindbar, Auswahl übersteht Neuladen
- [ ] Alle bisherigen Funktionen (bearbeiten, speichern, löschen, neu anlegen) erreichbar
- [ ] Alte Adressen und Umleitungen aus #634 funktionieren weiter
- [ ] Prüfungen grün, neue Tests vorher rot, Till hat abgenommen

## Nicht in diesem Plan

- Inhalt der Agenten-/Projekt-Formulare (`AgentFormTabs`, `ProjectFormTabs`) umbauen
- Optik von Skills-, Zugangsdaten- und Butler-Seite selbst
- Seiten-Kürzungen System, Module, User, Archiv, Dashboard (Schritt 3 ff.)
