# Plan: Hydra-Köpfe in den Box-Köpfen (Stufe 1 „freundlichere Boxen“)

Task 0dda5420. Till 27.10.2026: Boxen freundlicher machen, „fester Kopf nach Thema“.
Probe zuerst auf Buddy-Seite und Admin-Cockpit, dann entscheidet Till über Stufe 2
(eigene Bildchen für ~40 Kacheln).

## Ziel

Jede Box (`CockpitPanel`) und jedes Admin-Fenster (`AdminOverlay`) zeigt im Kopf links einen
kleinen Hydra-Kopf (36 px) und einen feinen Farbverlauf in dessen Farbe. Der Kopf richtet sich
nach dem **Thema** der Box, fest zugeordnet:

| Thema      | Kopf              | Farbe   | Beispiele |
|------------|-------------------|---------|-----------|
| `wissen`   | Professor (Brille)| amber   | Hinweis, Regeln, Sicherheitsregeln, Grundsatz, Hilfe, Zahnfee-Briefing |
| `werkzeug` | Macher (orange)   | orange  | Werkzeuge, Betriebszentrale, Integrationen, Wartung & Backups, Module, Plugins, Erweiterungen, VMs, Container, Nodes, Jobs, Automationen |
| `status`   | Denker (türkis)   | teal    | Status, Admin-Bereiche, Verlauf, Schon aktiv, In Arbeit, System, Projekt-Tasks, Dateien |
| `ideen`    | Träumer (lila)    | lavendel| Nächste Ausbaustufen, Optionale KI, Themes, KI-Modelle, MCP, Föderation |
| `kontakt`  | Buddy (mint)      | mint    | Buddy, Kontext, Benutzer, Zugangsdaten, Zugriff, Vault |

Boxen ohne Thema bleiben wie heute (kein Bild). Ein Modul kann seine Boxen später selbst
zuordnen (Prop), ohne Kern-Interna zu kennen.

## Dateien

- `frontend/src/shared/brand/boxThemes.ts` (neu): `BOX_THEMES` (Thema → Kopfbild, Name,
  Verlaufs-/Randfarbe) und `type BoxTheme`
- `frontend/src/shared/brand/BoxHead.tsx` (neu): kleiner Kopf als Deko (`alt=""`, `aria-hidden`,
  `loading="lazy"`), 36 px, Kreis im Themen-Ton
- `frontend/src/shared/brand/BoxHead.test.tsx` (neu)
- `frontend/src/features/cockpit/CockpitPanel.tsx`: neue Prop `theme?: BoxTheme`; mit Thema
  steht der Kopf links neben Eyebrow/Titel und oben läuft ein Verlauf im Themen-Ton
- `frontend/src/features/cockpit/CockpitPanel.test.tsx` (neu)
- `frontend/src/features/cockpit/admin/AdminOverlay.tsx`: neue Prop `theme?: BoxTheme`, Kopf
  links neben Eyebrow/Titel, Kopfleiste mit Verlauf
- `frontend/src/features/cockpit/admin/AdminOverlay.test.tsx` (neu)
- Zuordnung in den Seiten: `AdminCockpitPage.tsx` (8 Boxen), `BuddyPage.tsx` (3),
  `_BuddyBriefingBox.tsx` (1), `VaultCockpitPage.tsx` (3), `VaultStatusPanel.tsx` (2),
  `ProjectTasksPanel.tsx`, `ProjectFilesPanel.tsx`, und die 20 Admin-Fenster
- `frontend/src/shared/brand/boxThemes.test.ts` (neu): jedes Thema hat ein vorhandenes Bild;
  die Admin-Fenster-Zuordnung in `ADMIN_OVERLAY_THEME` ist vollständig für alle
  `AdminOverlayId`

## Implementierungsreihenfolge

### Task 1: Themen-Tabelle
- [ ] Test `boxThemes.test.ts`: fünf Themen; Bild je Thema liegt in `public/`; Namen
      Professor/Macher/Denker/Träumer/Buddy; jedes `AdminOverlayId` hat ein Thema
- [ ] RED → `boxThemes.ts` → GREEN; Mutante: falsches Bild → rot

### Task 2: Kopf-Baustein
- [ ] Test `BoxHead.test.tsx`: Bild des Themas, `alt=""`, `aria-hidden="true"`, `loading="lazy"`,
      Größe 36
- [ ] RED → `BoxHead.tsx` → GREEN

### Task 3: Boxen und Fenster
- [ ] Test `CockpitPanel.test.tsx`: ohne `theme` kein Bild (heutiges Aussehen); mit `theme`
      Kopfbild + Titel; Verlauf-Klasse vorhanden
- [ ] Test `AdminOverlay.test.tsx`: dasselbe für das Fenster (Titel, Schließen bleibt)
- [ ] RED → Umsetzung → GREEN; Mutante: Bild trotz fehlendem Thema → rot

### Task 4: Zuordnung in Seiten und Fenstern
- [ ] Admin-Fenster bekommen ihr Thema über `ADMIN_OVERLAY_THEME[id]` (eine Stelle)
- [ ] Boxen der Seiten bekommen `theme=` direkt
- [ ] Bestehende Tests grün

### Task 5: Prüfen
- [ ] tsc, eslint, vitest, Build
- [ ] Browser 1440/390 px: Buddy-Seite, Admin-Cockpit, drei Admin-Fenster; Kopf überdeckt
      keinen Text (Messung), Titel bleibt lesbar, auf dem Handy nicht zu groß
- [ ] Till zeigen → Freigabe für Stufe 2

## Nicht in diesem Plan

- Eigene Bildchen je Kachel/Knopf (Stufe 2, nach Tills Freigabe)
- Allgemeine Knöpfe (Schließen, Speichern) bleiben ohne Bild
- Boxen in Modulen (bringen ihr Thema später selbst mit)
