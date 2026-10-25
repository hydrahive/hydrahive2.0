# Spec: Butler-Editor zeigt Bausteine aus Modulen

> **Status:** Freigegeben (Till, 25.10.2026: „wir müssen den Butler sogar erweitern … der Butler sollte die treibende
> Kraft werden, um alles am Laufen zu halten“)
> **Anlass:** VoIP-Modul soll „Anruf kommt rein“ als Butler-Auslöser bringen (Task b37d9488, `telephony/PLAN-BUTLER.md`).
> **Task:** b37d9488

## 1. Befund (25.10.2026, gegen `main` e86358fe)

- Module können Butler-Bausteine registrieren (`ctx.register_butler_trigger/condition/action`,
  `modules/butler_bridge.py`); der Server kennt sie danach (Registry) und nimmt Abläufe mit ihnen beim Speichern an
  (`unknown_subtypes` prüft gegen die Registry).
- Die Oberfläche kennt nur fest eingebaute Bausteine: `frontend/src/features/butler/palette-data.ts`
  (`PALETTE_STRUCTURE`, `PALETTE_LABEL_KEY`, `defaultParams`) und `properties/registry.tsx` (`FORMS`). Ein
  Modul-Baustein erscheint nicht in der Palette und hätte kein Eingabeformular. Betroffen schon heute:
  cryptoboard `crypto_price` / `crypto_threshold`.
- Es gibt keinen Endpunkt, der die Registry ausliefert (siehe Kommentar in `palette-data.ts` zu
  `NOT_IMPLEMENTED_ACTIONS`).
- Jede `*Spec` hat bereits `label`, `description` und `params: list[ParamSchema]` (key, label, kind, required,
  options, placeholder, default) – genug, um ein Formular generisch zu bauen.

## 2. Ziel

1. Bausteine aus Modulen erscheinen im Editor in einer eigenen Gruppe **„Module“** (je Art Auslöser/Bedingung/Aktion
   mit der Farbe der Art) und lassen sich wie die eingebauten auf die Fläche ziehen.
2. Für sie baut der Editor das **Eingabeformular aus dem ParamSchema** (Feldarten `text`, `textarea`, `number`,
   `select`, `checkbox`, `list_text`, `time`). Pflichtfelder sind markiert; Vorgaben (`default`) werden beim Ablegen
   gesetzt.
3. Die Knoten-Vorschau zeigt die ersten gesetzten Werte (z. B. „bitcoin“).
4. Eingebaute Bausteine bleiben **unverändert** (eigene Formulare, eigene Texte) – kein Umbau der bestehenden
   Palette.

## 3. Umsetzung

### Server
- `GET /api/butler/registry` (angemeldet, jeder Nutzer): Liste aller Bausteine aus Modulen –
  `{type: "trigger"|"condition"|"action", subtype, label, description, module, params: [ParamSchema…],
  implemented}`. Eingebaute Bausteine werden **nicht** geliefert (die Oberfläche hat sie fest; vermeidet doppelte
  Pflege). Dazu merkt sich `butler_bridge` beim Einspeisen, welcher Subtype von welchem Modul kam.
- Keine Geheimnisse in der Antwort (nur Beschreibungen) → kein Admin-Schutz nötig.

### Oberfläche
- `butlerRegistry.ts`: lädt die Registry einmal beim Öffnen des Editors (`api.get("/butler/registry")`), bei Fehler
  leere Liste (Editor funktioniert wie bisher).
- `NodePalette`: zusätzliche Gruppe „Module“ unter den eingebauten, Einträge mit Modulnamen als Hinweis.
- `useButlerFlow.onDrop`: für Modul-Bausteine Vorgaben aus dem ParamSchema (`default`).
- `PropertiesPanel`: hat ein Subtype kein festes Formular, aber einen Registry-Eintrag → `SchemaForm`.
- `paramSummary`: Rückfall für Modul-Bausteine (erste zwei gesetzte Werte).
- Texte DE/EN für Gruppe, „aus Modul …“, „Pflichtfeld“.

## 4. Sicherheit
- Die Route liefert nur Beschreibungen, keine Daten. Ausführen bleibt wie heute (Server prüft Subtypes beim
  Speichern, Aktionen prüfen ihre Parameter selbst).
- Formularwerte aus dem SchemaForm sind reine Daten (kein HTML, kein Code); `select` nimmt nur angebotene Optionen.

## 5. Tests
- Server: Route liefert nur Modul-Bausteine mit Modul-Kennung und vollem ParamSchema; ohne Anmeldung 401; ein
  kollidierter (übersprungener) Modul-Baustein erscheint nicht.
- Oberfläche (vitest): Palette zeigt Gruppe „Module“ nur bei vorhandenen Bausteinen; SchemaForm baut je Feldart das
  richtige Feld, setzt Werte, `select` nur mit Optionen; Vorgaben beim Ablegen; Vorschau-Rückfall.
- Gegenprobe: eingebaute Bausteine unverändert (vorhandene Tests grün).

## 6. Nicht in dieser Spec
- Umbau der eingebauten Bausteine auf die Registry.
- Neue Butler-Fähigkeiten (Warten/Verzögern, Ablaufbesitzer an Aktionen) – eigene Specs.
